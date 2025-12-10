"""
Regression Analysis Component Example

This example demonstrates how to create a data processing component that performs
regression analysis against a baseline model. The component can:
- Accept historical data from Koios tags (via bindings)
- Maintain its own internal history
- Compare current data against a baseline regression model
- Detect deviations and anomalies
"""

from typing import Dict, Any, List, Optional, Tuple
import math
import time
from collections import deque

from koios_component_sdk.base import ProcessorComponent
from koios_component_sdk.base.component import ComponentMetadata, ParameterDefinition, ComponentCategory
from koios_component_sdk.decorators import validate_parameters, bind_to_tag, on_start, on_stop


class RegressionAnalyzer(ProcessorComponent):
    """
    Regression Analysis Component for comparing data against a baseline model.
    
    Features:
    - Linear regression analysis
    - Baseline model comparison
    - Deviation detection
    - Support for Koios history or internal history
    - Statistical metrics (R², RMSE, MAE)
    - Anomaly detection thresholds
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        super().__init__(component_id, parameters)
        
        # Baseline model parameters (y = slope * x + intercept)
        self._baseline_slope = parameters.get('baseline_slope', 1.0)
        self._baseline_intercept = parameters.get('baseline_intercept', 0.0)
        self._baseline_r_squared = parameters.get('baseline_r_squared', 1.0)
        
        # Data source configuration
        self._use_koios_history = parameters.get('use_koios_history', False)
        self._history_window_size = parameters.get('history_window_size', 100)
        self._min_samples_for_analysis = parameters.get('min_samples_for_analysis', 10)
        
        # Internal history storage (if not using Koios history)
        self._internal_history: deque = deque(maxlen=self._history_window_size)
        
        # Anomaly detection thresholds
        self._deviation_threshold = parameters.get('deviation_threshold', 2.0)  # Standard deviations
        self._rmse_threshold = parameters.get('rmse_threshold', None)
        self._mae_threshold = parameters.get('mae_threshold', None)
        
        # Current regression model (calculated from data)
        self._current_slope: Optional[float] = None
        self._current_intercept: Optional[float] = None
        self._current_r_squared: Optional[float] = None
        self._current_rmse: Optional[float] = None
        self._current_mae: Optional[float] = None
        
        # Statistics
        self._anomaly_count = 0
        self._total_analyzed = 0
        self._last_analysis_time: Optional[float] = None
        
        # Input values (can be set via bindings or process_data)
        self._input_x_value: Optional[float] = None
        self._input_y_value: Optional[float] = None
    
    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="Regression Analyzer",
            version="1.0.0",
            author="Koios SDK Example",
            description="Regression analysis component comparing data against baseline model with anomaly detection",
            category=ComponentCategory.PROCESSING,
            koios_version_min="1.0.0",
            tags=["regression", "analysis", "statistics", "anomaly-detection", "baseline"]
        )
    
    @property
    def parameter_definitions(self) -> List[ParameterDefinition]:
        return [
            # Baseline model parameters
            ParameterDefinition(
                name="baseline_slope",
                type="float",
                description="Slope of the baseline regression model (y = slope * x + intercept)",
                default=1.0,
                required=False
            ),
            ParameterDefinition(
                name="baseline_intercept",
                type="float",
                description="Intercept of the baseline regression model",
                default=0.0,
                required=False
            ),
            ParameterDefinition(
                name="baseline_r_squared",
                type="float",
                description="R-squared value of the baseline model (for comparison)",
                default=1.0,
                min_value=0.0,
                max_value=1.0,
                required=False
            ),
            
            # Data source configuration
            ParameterDefinition(
                name="use_koios_history",
                type="boolean",
                description="If true, fetch historical data from Koios tags; if false, use internal history",
                default=False,
                required=False
            ),
            ParameterDefinition(
                name="history_window_size",
                type="integer",
                description="Maximum number of data points to keep in history",
                default=100,
                min_value=10,
                max_value=10000,
                required=False
            ),
            ParameterDefinition(
                name="min_samples_for_analysis",
                type="integer",
                description="Minimum number of samples required before performing regression analysis",
                default=10,
                min_value=3,
                required=False
            ),
            
            # Anomaly detection thresholds
            ParameterDefinition(
                name="deviation_threshold",
                type="float",
                description="Number of standard deviations for anomaly detection",
                default=2.0,
                min_value=0.0,
                required=False
            ),
            ParameterDefinition(
                name="rmse_threshold",
                type="float",
                description="Root Mean Square Error threshold for anomaly detection (None to disable)",
                default=None,
                min_value=0.0,
                required=False
            ),
            ParameterDefinition(
                name="mae_threshold",
                type="float",
                description="Mean Absolute Error threshold for anomaly detection (None to disable)",
                default=None,
                min_value=0.0,
                required=False
            ),
            
            # Processing parameters (inherited from ProcessorComponent)
            ParameterDefinition(
                name="buffer_size",
                type="integer",
                description="Size of input/output buffers",
                default=1000,
                min_value=10,
                required=False
            ),
            ParameterDefinition(
                name="batch_size",
                type="integer",
                description="Number of data points to process per batch",
                default=1,
                min_value=1,
                required=False
            ),
            ParameterDefinition(
                name="processing_interval",
                type="float",
                description="Processing interval in seconds",
                default=1.0,
                min_value=0.1,
                required=False
            ),
        ]
    
    @bind_to_tag("regression_input_x", direction="input")
    def input_x(self) -> Optional[float]:
        """X input tag (independent variable) from Koios."""
        return self._input_x_value
    
    @bind_to_tag("regression_input_y", direction="input")
    def input_y(self) -> Optional[float]:
        """Y input tag (dependent variable) from Koios."""
        return self._input_y_value
    
    def set_input_x(self, value: float):
        """Set X input value (called by framework when tag updates)."""
        self._input_x_value = value
        if self._input_x_value is not None and self._input_y_value is not None:
            self._add_data_point(self._input_x_value, self._input_y_value)
    
    def set_input_y(self, value: float):
        """Set Y input value (called by framework when tag updates)."""
        self._input_y_value = value
        if self._input_x_value is not None and self._input_y_value is not None:
            self._add_data_point(self._input_x_value, self._input_y_value)
    
    # Output bindings for analysis results
    @bind_to_tag("regression_current_slope", direction="output")
    def current_slope(self) -> Optional[float]:
        """Current calculated regression slope."""
        return self._current_slope
    
    @bind_to_tag("regression_current_intercept", direction="output")
    def current_intercept(self) -> Optional[float]:
        """Current calculated regression intercept."""
        return self._current_intercept
    
    @bind_to_tag("regression_r_squared", direction="output")
    def r_squared(self) -> Optional[float]:
        """R-squared value of current regression."""
        return self._current_r_squared
    
    @bind_to_tag("regression_rmse", direction="output")
    def rmse(self) -> Optional[float]:
        """Root Mean Square Error."""
        return self._current_rmse
    
    @bind_to_tag("regression_mae", direction="output")
    def mae(self) -> Optional[float]:
        """Mean Absolute Error."""
        return self._current_mae
    
    @bind_to_tag("regression_anomaly_count", direction="output")
    def anomaly_count(self) -> int:
        """Number of anomalies detected."""
        return self._anomaly_count
    
    @bind_to_tag("regression_slope_deviation", direction="output")
    def slope_deviation(self) -> Optional[float]:
        """Deviation of current slope from baseline."""
        if self._current_slope is not None:
            return abs(self._current_slope - self._baseline_slope)
        return None
    
    @bind_to_tag("regression_intercept_deviation", direction="output")
    def intercept_deviation(self) -> Optional[float]:
        """Deviation of current intercept from baseline."""
        if self._current_intercept is not None:
            return abs(self._current_intercept - self._baseline_intercept)
        return None
    
    @bind_to_tag("regression_analysis_status", direction="output")
    def analysis_status(self) -> str:
        """Status of the analysis."""
        if self._last_result is None:
            return "not_started"
        return self._last_result.get('status', 'unknown')
    
    def _add_data_point(self, x: float, y: float):
        """Add a data point to history."""
        timestamp = time.time()
        data_point = {
            'timestamp': timestamp,
            'x': x,
            'y': y
        }
        
        if self._use_koios_history:
            # When using Koios history, data points come via process_data
            # This method is for internal history mode
            pass
        else:
            # Add to internal history
            self._internal_history.append(data_point)
            # Also add to input buffer for processing
            self.add_input_data(data_point)
    
    def _get_history_data(self) -> List[Dict[str, Any]]:
        """Get historical data from either Koios or internal storage."""
        if self._use_koios_history:
            # In real implementation, this would fetch from Koios history API
            # For now, we'll use the input buffer which should contain historical data
            # when fetched from Koios
            return list(self._input_buffer)
        else:
            return list(self._internal_history)
    
    def _calculate_regression(self, data_points: List[Dict[str, Any]]) -> Tuple[float, float, float, float, float]:
        """
        Calculate linear regression from data points.
        
        Returns:
            Tuple of (slope, intercept, r_squared, rmse, mae)
        """
        if len(data_points) < 2:
            return None, None, None, None, None
        
        # Extract x and y values
        x_values = [dp['x'] for dp in data_points]
        y_values = [dp['y'] for dp in data_points]
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x_squared = sum(x * x for x in x_values)
        sum_y_squared = sum(y * y for y in y_values)
        
        # Calculate slope and intercept
        denominator = n * sum_x_squared - sum_x * sum_x
        if abs(denominator) < 1e-10:
            return None, None, None, None, None
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate R-squared
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values))
        
        if ss_tot < 1e-10:
            r_squared = 1.0
        else:
            r_squared = 1.0 - (ss_res / ss_tot)
        
        # Calculate RMSE (Root Mean Square Error)
        rmse = math.sqrt(ss_res / n)
        
        # Calculate MAE (Mean Absolute Error)
        mae = sum(abs(y - (slope * x + intercept)) for x, y in zip(x_values, y_values)) / n
        
        return slope, intercept, r_squared, rmse, mae
    
    def _detect_anomalies(self, data_points: List[Dict[str, Any]], 
                         slope: float, intercept: float) -> List[Dict[str, Any]]:
        """
        Detect anomalies in data points based on deviation from regression model.
        
        Returns:
            List of anomaly dictionaries with details
        """
        anomalies = []
        
        if slope is None or intercept is None:
            return anomalies
        
        # Calculate residuals
        residuals = []
        for dp in data_points:
            predicted = slope * dp['x'] + intercept
            residual = dp['y'] - predicted
            residuals.append(residual)
        
        if len(residuals) < 2:
            return anomalies
        
        # Calculate mean and standard deviation of residuals
        mean_residual = sum(residuals) / len(residuals)
        variance = sum((r - mean_residual) ** 2 for r in residuals) / len(residuals)
        std_residual = math.sqrt(variance) if variance > 0 else 0.0
        
        if std_residual < 1e-10:
            return anomalies
        
        # Detect anomalies based on standard deviation threshold
        for i, (dp, residual) in enumerate(zip(data_points, residuals)):
            z_score = abs((residual - mean_residual) / std_residual)
            
            if z_score > self._deviation_threshold:
                anomalies.append({
                    'timestamp': dp['timestamp'],
                    'x': dp['x'],
                    'y': dp['y'],
                    'predicted': slope * dp['x'] + intercept,
                    'residual': residual,
                    'z_score': z_score,
                    'deviation': z_score * std_residual
                })
        
        return anomalies
    
    def process_data(self, data: List[Any]) -> Any:
        """
        Process input data and perform regression analysis.
        
        Args:
            data: List of data points (dicts with 'x', 'y', 'timestamp')
            
        Returns:
            Analysis result dictionary
        """
        try:
            # Get all available history
            history_data = self._get_history_data()
            
            # Add new data points to history if not already there
            for dp in data:
                if isinstance(dp, dict) and 'x' in dp and 'y' in dp:
                    if dp not in history_data:
                        if not self._use_koios_history:
                            self._internal_history.append(dp)
                        history_data.append(dp)
            
            # Ensure we have enough samples
            if len(history_data) < self._min_samples_for_analysis:
                return {
                    'status': 'insufficient_data',
                    'samples': len(history_data),
                    'required': self._min_samples_for_analysis,
                    'message': f'Need at least {self._min_samples_for_analysis} samples for analysis'
                }
            
            # Calculate current regression
            slope, intercept, r_squared, rmse, mae = self._calculate_regression(history_data)
            
            if slope is None:
                return {
                    'status': 'error',
                    'message': 'Failed to calculate regression (insufficient variance)'
                }
            
            # Update current model
            self._current_slope = slope
            self._current_intercept = intercept
            self._current_r_squared = r_squared
            self._current_rmse = rmse
            self._current_mae = mae
            
            # Compare with baseline
            slope_deviation = abs(slope - self._baseline_slope)
            intercept_deviation = abs(intercept - self._baseline_intercept)
            r_squared_change = r_squared - self._baseline_r_squared
            
            # Detect anomalies
            anomalies = self._detect_anomalies(history_data, slope, intercept)
            
            # Check thresholds
            threshold_violations = []
            if self._rmse_threshold is not None and rmse > self._rmse_threshold:
                threshold_violations.append(f'RMSE threshold exceeded: {rmse:.4f} > {self._rmse_threshold}')
            if self._mae_threshold is not None and mae > self._mae_threshold:
                threshold_violations.append(f'MAE threshold exceeded: {mae:.4f} > {self._mae_threshold}')
            
            # Update statistics
            self._total_analyzed += len(data)
            self._anomaly_count += len(anomalies)
            self._last_analysis_time = time.time()
            
            # Build result
            result = {
                'status': 'success',
                'timestamp': time.time(),
                'samples_analyzed': len(history_data),
                'current_model': {
                    'slope': slope,
                    'intercept': intercept,
                    'r_squared': r_squared,
                    'rmse': rmse,
                    'mae': mae
                },
                'baseline_model': {
                    'slope': self._baseline_slope,
                    'intercept': self._baseline_intercept,
                    'r_squared': self._baseline_r_squared
                },
                'comparison': {
                    'slope_deviation': slope_deviation,
                    'intercept_deviation': intercept_deviation,
                    'r_squared_change': r_squared_change
                },
                'anomalies': {
                    'count': len(anomalies),
                    'detected': anomalies[:10]  # Limit to first 10 for output
                },
                'threshold_violations': threshold_violations,
                'statistics': {
                    'total_analyzed': self._total_analyzed,
                    'total_anomalies': self._anomaly_count,
                    'anomaly_rate': self._anomaly_count / max(self._total_analyzed, 1)
                }
            }
            
            self.logger.debug(f"Regression analysis completed: {len(history_data)} samples, "
                            f"R²={r_squared:.4f}, RMSE={rmse:.4f}, {len(anomalies)} anomalies")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing data: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @on_start
    def initialize_regression(self):
        """Initialize regression analyzer on start."""
        self.logger.info(f"Regression Analyzer started - Baseline: y = {self._baseline_slope:.4f}x + {self._baseline_intercept:.4f}")
        self.logger.info(f"Using {'Koios history' if self._use_koios_history else 'internal history'}")
    
    @on_stop
    def cleanup_regression(self):
        """Cleanup on stop."""
        self.logger.info(f"Regression Analyzer stopped - Analyzed {self._total_analyzed} samples, "
                        f"detected {self._anomaly_count} anomalies")
    
    def get_current_model(self) -> Dict[str, Any]:
        """Get the current regression model parameters."""
        return {
            'slope': self._current_slope,
            'intercept': self._current_intercept,
            'r_squared': self._current_r_squared,
            'rmse': self._current_rmse,
            'mae': self._current_mae
        }
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of analysis results."""
        return {
            'current_model': self.get_current_model(),
            'baseline_model': {
                'slope': self._baseline_slope,
                'intercept': self._baseline_intercept,
                'r_squared': self._baseline_r_squared
            },
            'statistics': {
                'total_analyzed': self._total_analyzed,
                'total_anomalies': self._anomaly_count,
                'anomaly_rate': self._anomaly_count / max(self._total_analyzed, 1),
                'history_size': len(self._internal_history) if not self._use_koios_history else self.input_buffer_size,
                'last_analysis_time': self._last_analysis_time
            }
        }

