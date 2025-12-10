# Regression Analyzer Component

A data processing component for performing regression analysis against a baseline model. This component can compare current data trends against an established baseline, detect anomalies, and provide statistical metrics.

## Features

- **Linear Regression Analysis**: Calculates slope, intercept, R², RMSE, and MAE from data points
- **Baseline Comparison**: Compares current regression model against a predefined baseline
- **Anomaly Detection**: Identifies data points that deviate significantly from the regression model
- **Dual History Modes**: 
  - **Koios History Mode**: Fetches historical data from Koios tags
  - **Internal History Mode**: Maintains its own internal history buffer
- **Statistical Metrics**: Provides comprehensive regression statistics
- **Threshold Monitoring**: Configurable thresholds for RMSE and MAE

## Use Cases

- **Process Monitoring**: Compare current process behavior against historical baseline
- **Quality Control**: Detect deviations in product quality metrics
- **Predictive Maintenance**: Identify trends that deviate from normal operation
- **Performance Analysis**: Track performance metrics against expected models
- **Anomaly Detection**: Find outliers in time-series data

## Component Parameters

### Baseline Model Parameters

- `baseline_slope` (float, default: 1.0): Slope of the baseline regression model
- `baseline_intercept` (float, default: 0.0): Intercept of the baseline regression model
- `baseline_r_squared` (float, default: 1.0): R-squared value of the baseline model (0-1)

### Data Source Configuration

- `use_koios_history` (boolean, default: false): 
  - `true`: Fetch historical data from Koios tags
  - `false`: Use internal history buffer
- `history_window_size` (integer, default: 100): Maximum number of data points to keep
- `min_samples_for_analysis` (integer, default: 10): Minimum samples required for analysis

### Anomaly Detection

- `deviation_threshold` (float, default: 2.0): Number of standard deviations for anomaly detection
- `rmse_threshold` (float, optional): RMSE threshold for anomaly alerts
- `mae_threshold` (float, optional): MAE threshold for anomaly alerts

### Processing Parameters

- `buffer_size` (integer, default: 1000): Size of input/output buffers
- `batch_size` (integer, default: 1): Number of data points to process per batch
- `processing_interval` (float, default: 1.0): Processing interval in seconds

## Tag Bindings

### Input Tags

- `regression_input_x`: Independent variable (X) - current value or historical data
- `regression_input_y`: Dependent variable (Y) - current value or historical data

### Output Tags

- `regression_current_slope`: Current calculated regression slope
- `regression_current_intercept`: Current calculated regression intercept
- `regression_r_squared`: R-squared value of current regression
- `regression_rmse`: Root Mean Square Error
- `regression_mae`: Mean Absolute Error
- `regression_anomaly_count`: Number of anomalies detected
- `regression_slope_deviation`: Deviation from baseline slope
- `regression_intercept_deviation`: Deviation from baseline intercept
- `regression_analysis_status`: Analysis status (success, insufficient_data, error)

## Usage Examples

### Example 1: Basic Usage with Internal History

```python
from koios_component_sdk.base import RegressionAnalyzer

# Initialize component with baseline model
parameters = {
    'baseline_slope': 2.5,
    'baseline_intercept': 10.0,
    'baseline_r_squared': 0.95,
    'use_koios_history': False,
    'history_window_size': 100,
    'min_samples_for_analysis': 10,
    'deviation_threshold': 2.0
}

component = RegressionAnalyzer('regression_001', parameters)
component.initialize()
component.start()

# Add data points
for i in range(20):
    x = i
    y = 2.5 * x + 10.0 + (i % 3)  # Baseline with small variations
    component.add_input_data({'x': x, 'y': y, 'timestamp': time.time()})
    component.execute()

# Get analysis results
result = component.last_result
print(f"Current slope: {result['current_model']['slope']}")
print(f"Anomalies detected: {result['anomalies']['count']}")
```

### Example 2: Using Koios History

```python
# Configure component to use Koios history
parameters = {
    'baseline_slope': 1.8,
    'baseline_intercept': 5.0,
    'use_koios_history': True,  # Enable Koios history mode
    'history_window_size': 200,
    'min_samples_for_analysis': 20
}

component = RegressionAnalyzer('regression_002', parameters)
component.initialize()
component.start()

# Bind to Koios tags
component.set_input_x(koios_tag_value_x)  # From Koios tag
component.set_input_y(koios_tag_value_y)  # From Koios tag

# Component will fetch historical data from Koios automatically
component.execute()
```

### Example 3: Anomaly Detection with Thresholds

```python
parameters = {
    'baseline_slope': 1.0,
    'baseline_intercept': 0.0,
    'deviation_threshold': 2.5,  # 2.5 standard deviations
    'rmse_threshold': 5.0,      # Alert if RMSE > 5.0
    'mae_threshold': 3.0,        # Alert if MAE > 3.0
    'min_samples_for_analysis': 15
}

component = RegressionAnalyzer('regression_003', parameters)
component.initialize()
component.start()

# Process data
result = component.execute()

if result['success']:
    analysis = result['last_result']
    
    # Check for threshold violations
    if analysis['threshold_violations']:
        print("ALERT: Threshold violations detected!")
        for violation in analysis['threshold_violations']:
            print(f"  - {violation}")
    
    # Check for anomalies
    if analysis['anomalies']['count'] > 0:
        print(f"Found {analysis['anomalies']['count']} anomalies:")
        for anomaly in analysis['anomalies']['detected']:
            print(f"  - At x={anomaly['x']}, y={anomaly['y']}, "
                  f"deviation={anomaly['deviation']:.2f}")
```

### Example 4: Monitoring Process Performance

```python
# Set up baseline from historical good performance
parameters = {
    'baseline_slope': 0.05,      # Expected efficiency improvement per day
    'baseline_intercept': 85.0,  # Baseline efficiency percentage
    'baseline_r_squared': 0.92,  # Good fit expected
    'use_koios_history': True,
    'deviation_threshold': 2.0,
    'rmse_threshold': 2.5       # Alert if model fit degrades
}

component = RegressionAnalyzer('efficiency_monitor', parameters)
component.initialize()
component.start()

# Continuously monitor
while component.status == ComponentStatus.RUNNING:
    component.execute()
    summary = component.get_analysis_summary()
    
    # Check if performance is degrading
    if summary['current_model']['r_squared'] < 0.85:
        print("WARNING: Model fit degraded!")
    
    if summary['statistics']['anomaly_rate'] > 0.1:
        print("WARNING: High anomaly rate detected!")
    
    time.sleep(component.parameters['processing_interval'])
```

## Analysis Output Structure

The component returns a detailed analysis result:

```python
{
    'status': 'success',  # or 'insufficient_data', 'error'
    'timestamp': 1234567890.0,
    'samples_analyzed': 50,
    'current_model': {
        'slope': 2.45,
        'intercept': 10.2,
        'r_squared': 0.94,
        'rmse': 1.23,
        'mae': 0.98
    },
    'baseline_model': {
        'slope': 2.5,
        'intercept': 10.0,
        'r_squared': 0.95
    },
    'comparison': {
        'slope_deviation': 0.05,
        'intercept_deviation': 0.2,
        'r_squared_change': -0.01
    },
    'anomalies': {
        'count': 3,
        'detected': [
            {
                'timestamp': 1234567890.0,
                'x': 15.0,
                'y': 50.0,
                'predicted': 46.95,
                'residual': 3.05,
                'z_score': 2.3,
                'deviation': 3.05
            },
            # ... more anomalies
        ]
    },
    'threshold_violations': [],
    'statistics': {
        'total_analyzed': 100,
        'total_anomalies': 5,
        'anomaly_rate': 0.05
    }
}
```

## Statistical Metrics Explained

- **Slope**: Rate of change (dy/dx) in the linear relationship
- **Intercept**: Y-value when X=0
- **R-squared (R²)**: Coefficient of determination (0-1), measures how well the model fits the data
  - 1.0 = perfect fit
  - 0.0 = no correlation
- **RMSE**: Root Mean Square Error - average magnitude of prediction errors
- **MAE**: Mean Absolute Error - average absolute difference between predicted and actual values
- **Z-score**: Number of standard deviations a data point is from the mean

## Best Practices

1. **Baseline Establishment**: Establish baseline model from historical "good" data
2. **Sample Size**: Ensure sufficient samples (`min_samples_for_analysis`) before analysis
3. **Threshold Tuning**: Adjust `deviation_threshold` based on process variability
4. **History Window**: Set `history_window_size` based on data rate and analysis needs
5. **Processing Interval**: Match `processing_interval` to your data update frequency
6. **Anomaly Review**: Review detected anomalies to refine thresholds

## Limitations

- Currently supports linear regression only (y = mx + b)
- Requires minimum of 3 samples for regression calculation
- Anomaly detection based on statistical deviation (may flag legitimate outliers)
- Internal history is limited by `history_window_size`

## Future Enhancements

- Support for polynomial regression
- Multiple regression (multiple independent variables)
- Time-weighted regression
- Adaptive baseline models
- Integration with Koios history API for historical data retrieval

## License

MIT

