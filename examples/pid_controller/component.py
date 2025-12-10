"""
Advanced PID Controller Example

This example demonstrates how to create a sophisticated PID controller component
using the Koios Component SDK. It includes features like anti-windup, derivative
filtering, and gain scheduling.
"""

from typing import Dict, Any, List
import math

from koios_component_sdk.base import ControllerComponent
from koios_component_sdk.base.component import ComponentMetadata, ParameterDefinition, ComponentCategory
from koios_component_sdk.decorators import validate_parameters, bind_to_tag, on_start, on_stop


class AdvancedPIDController(ControllerComponent):
    """
    Advanced PID Controller with anti-windup and derivative filtering.
    
    Features:
    - Standard PID control algorithm
    - Integral windup protection
    - Derivative term filtering
    - Gain scheduling support
    - Manual/automatic mode switching
    - Output rate limiting
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        super().__init__(component_id, parameters)
        
        # PID gains
        self._kp = parameters.get('kp', 1.0)
        self._ki = parameters.get('ki', 0.1)
        self._kd = parameters.get('kd', 0.01)
        
        # Anti-windup
        self._integral_min = parameters.get('integral_min', -100.0)
        self._integral_max = parameters.get('integral_max', 100.0)
        
        # Derivative filtering
        self._derivative_filter_time = parameters.get('derivative_filter_time', 0.1)
        self._filtered_derivative = 0.0
        
        # Rate limiting
        self._output_rate_limit = parameters.get('output_rate_limit', None)
        self._previous_output = 0.0
        
        # Gain scheduling
        self._gain_schedule_enabled = parameters.get('gain_schedule_enabled', False)
        self._gain_schedule_points = parameters.get('gain_schedule_points', [])
        
        # Statistics
        self._integral_saturation_count = 0
        self._rate_limit_count = 0
    
    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            name="Advanced PID Controller",
            version="1.1.0",
            author="Koios SDK Example",
            description="Advanced PID controller with anti-windup, derivative filtering, and gain scheduling",
            category=ComponentCategory.CONTROL,
            koios_version_min="1.1.0",
            tags=["pid", "control", "advanced", "anti-windup"]
        )
    
    @property
    def parameter_definitions(self) -> List[ParameterDefinition]:
        return [
            # Basic PID parameters
            ParameterDefinition(
                name="kp",
                type="float",
                description="Proportional gain",
                default=1.0,
                min_value=0.0
            ),
            ParameterDefinition(
                name="ki",
                type="float",
                description="Integral gain",
                default=0.1,
                min_value=0.0
            ),
            ParameterDefinition(
                name="kd",
                type="float",
                description="Derivative gain",
                default=0.01,
                min_value=0.0
            ),
            
            # Anti-windup parameters
            ParameterDefinition(
                name="integral_min",
                type="float",
                description="Minimum integral term value",
                default=-100.0
            ),
            ParameterDefinition(
                name="integral_max",
                type="float",
                description="Maximum integral term value",
                default=100.0
            ),
            
            # Derivative filtering
            ParameterDefinition(
                name="derivative_filter_time",
                type="float",
                description="Derivative filter time constant (seconds)",
                default=0.1,
                min_value=0.001
            ),
            
            # Rate limiting
            ParameterDefinition(
                name="output_rate_limit",
                type="float",
                description="Maximum output change rate per second (None for no limit)",
                default=None,
                min_value=0.0
            ),
            
            # Gain scheduling
            ParameterDefinition(
                name="gain_schedule_enabled",
                type="boolean",
                description="Enable gain scheduling based on process variable",
                default=False
            ),
            ParameterDefinition(
                name="gain_schedule_points",
                type="json",
                description="Gain scheduling points as list of [pv, kp_mult, ki_mult, kd_mult]",
                default=[]
            ),
        ]
    
    @bind_to_tag("pid_setpoint", direction="input")
    def setpoint(self) -> float:
        """Setpoint input from Koios tag."""
        return self._setpoint
    
    @bind_to_tag("pid_process_variable", direction="input") 
    def process_variable(self) -> float:
        """Process variable input from Koios tag."""
        return self._process_variable
    
    @bind_to_tag("pid_output", direction="output")
    def output(self) -> float:
        """Control output to Koios tag."""
        return self.output
    
    @bind_to_tag("pid_error", direction="output")
    def error(self) -> float:
        """Current error to Koios tag."""
        return self._error
    
    @bind_to_tag("pid_integral_term", direction="output")
    def integral_term(self) -> float:
        """Integral term for monitoring."""
        return self._ki * self._error_sum
    
    @bind_to_tag("pid_derivative_term", direction="output")
    def derivative_term(self) -> float:
        """Derivative term for monitoring."""
        return self._kd * self._filtered_derivative
    
    def get_bindable_fields(self) -> List[str]:
        """Extended bindable fields for advanced PID."""
        base_fields = super().get_bindable_fields()
        return base_fields + [
            "integral_term",
            "derivative_term", 
            "integral_saturation_count",
            "rate_limit_count",
            "effective_kp",
            "effective_ki",
            "effective_kd"
        ]
    
    @on_start
    def initialize_pid_parameters(self):
        """Initialize PID parameters on start."""
        self._kp = self.get_parameter('kp', 1.0)
        self._ki = self.get_parameter('ki', 0.1)
        self._kd = self.get_parameter('kd', 0.01)
        self._integral_min = self.get_parameter('integral_min', -100.0)
        self._integral_max = self.get_parameter('integral_max', 100.0)
        self._derivative_filter_time = self.get_parameter('derivative_filter_time', 0.1)
        self._output_rate_limit = self.get_parameter('output_rate_limit')
        self._gain_schedule_enabled = self.get_parameter('gain_schedule_enabled', False)
        self._gain_schedule_points = self.get_parameter('gain_schedule_points', [])
        
        self.logger.info("Advanced PID parameters initialized")
    
    @on_stop
    def cleanup_pid(self):
        """Cleanup on stop."""
        self.logger.info(f"PID Statistics - Integral saturations: {self._integral_saturation_count}, "
                        f"Rate limits: {self._rate_limit_count}")
    
    def _calculate_scheduled_gains(self) -> tuple[float, float, float]:
        """Calculate gains based on gain scheduling."""
        if not self._gain_schedule_enabled or not self._gain_schedule_points:
            return self._kp, self._ki, self._kd
        
        pv = self._process_variable
        
        # Find the appropriate gain schedule points
        points = sorted(self._gain_schedule_points, key=lambda x: x[0])
        
        # If PV is below the first point, use first point gains
        if pv <= points[0][0]:
            _, kp_mult, ki_mult, kd_mult = points[0]
            return self._kp * kp_mult, self._ki * ki_mult, self._kd * kd_mult
        
        # If PV is above the last point, use last point gains
        if pv >= points[-1][0]:
            _, kp_mult, ki_mult, kd_mult = points[-1]
            return self._kp * kp_mult, self._ki * ki_mult, self._kd * kd_mult
        
        # Interpolate between points
        for i in range(len(points) - 1):
            pv1, kp1, ki1, kd1 = points[i]
            pv2, kp2, ki2, kd2 = points[i + 1]
            
            if pv1 <= pv <= pv2:
                # Linear interpolation
                ratio = (pv - pv1) / (pv2 - pv1)
                kp_mult = kp1 + ratio * (kp2 - kp1)
                ki_mult = ki1 + ratio * (ki2 - ki1)
                kd_mult = kd1 + ratio * (kd2 - kd1)
                
                return self._kp * kp_mult, self._ki * ki_mult, self._kd * kd_mult
        
        # Fallback to base gains
        return self._kp, self._ki, self._kd
    
    def _apply_derivative_filter(self, raw_derivative: float) -> float:
        """Apply first-order filter to derivative term."""
        if self._derivative_filter_time <= 0:
            return raw_derivative
        
        # First-order low-pass filter
        alpha = self._dt / (self._derivative_filter_time + self._dt)
        self._filtered_derivative = (1 - alpha) * self._filtered_derivative + alpha * raw_derivative
        
        return self._filtered_derivative
    
    def _apply_integral_windup_protection(self, integral_term: float) -> float:
        """Apply anti-windup protection to integral term."""
        if integral_term > self._integral_max:
            self._integral_saturation_count += 1
            return self._integral_max
        elif integral_term < self._integral_min:
            self._integral_saturation_count += 1
            return self._integral_min
        else:
            return integral_term
    
    def _apply_output_rate_limiting(self, new_output: float) -> float:
        """Apply rate limiting to output."""
        if self._output_rate_limit is None:
            return new_output
        
        max_change = self._output_rate_limit * self._dt
        output_change = new_output - self._previous_output
        
        if abs(output_change) > max_change:
            self._rate_limit_count += 1
            if output_change > 0:
                limited_output = self._previous_output + max_change
            else:
                limited_output = self._previous_output - max_change
            
            self.logger.debug(f"Output rate limited: {new_output:.3f} -> {limited_output:.3f}")
            return limited_output
        
        return new_output
    
    @validate_parameters
    def compute_output(self) -> float:
        """Compute PID output with advanced features."""
        # Get scheduled gains
        kp, ki, kd = self._calculate_scheduled_gains()
        
        # Proportional term
        proportional = kp * self._error
        
        # Integral term with anti-windup
        self._error_sum += self._error * self._dt
        integral_raw = ki * self._error_sum
        integral_protected = self._apply_integral_windup_protection(integral_raw)
        
        # Update error sum based on protected integral (back-calculation anti-windup)
        if integral_protected != integral_raw:
            self._error_sum = integral_protected / ki if ki != 0 else 0
        
        # Derivative term with filtering
        raw_derivative = (self._error - self._previous_error) / self._dt if self._dt > 0 else 0
        filtered_derivative = self._apply_derivative_filter(raw_derivative)
        derivative = kd * filtered_derivative
        
        # Compute total output
        total_output = proportional + integral_protected + derivative
        
        # Apply output limits (from base class)
        limited_output = self._clamp_output(total_output)
        
        # Apply rate limiting
        rate_limited_output = self._apply_output_rate_limiting(limited_output)
        
        # Store for next iteration
        self._previous_output = rate_limited_output
        
        # Log detailed information periodically
        if self._execution_count % 100 == 0:  # Every 100 executions
            self.logger.debug(
                f"PID: SP={self._setpoint:.2f}, PV={self._process_variable:.2f}, "
                f"Error={self._error:.2f}, P={proportional:.2f}, I={integral_protected:.2f}, "
                f"D={derivative:.2f}, Output={rate_limited_output:.2f}"
            )
        
        return rate_limited_output
    
    def get_advanced_stats(self) -> Dict[str, Any]:
        """Get advanced PID statistics."""
        kp, ki, kd = self._calculate_scheduled_gains()
        
        return {
            "effective_kp": kp,
            "effective_ki": ki,
            "effective_kd": kd,
            "integral_term": ki * self._error_sum,
            "derivative_term": kd * self._filtered_derivative,
            "integral_saturation_count": self._integral_saturation_count,
            "rate_limit_count": self._rate_limit_count,
            "filtered_derivative": self._filtered_derivative,
            "gain_schedule_active": self._gain_schedule_enabled
        }
    
    def reset(self):
        """Enhanced reset with advanced features."""
        super().reset()
        self._filtered_derivative = 0.0
        self._previous_output = 0.0
        self._integral_saturation_count = 0
        self._rate_limit_count = 0
        self.logger.info("Advanced PID reset completed")


# Example usage and testing
if __name__ == "__main__":
    # Example configuration for a temperature control application
    config = {
        "kp": 2.0,
        "ki": 0.5,
        "kd": 0.1,
        "sample_time": 1.0,
        "output_min": 0.0,
        "output_max": 100.0,
        "integral_min": -50.0,
        "integral_max": 50.0,
        "derivative_filter_time": 0.2,
        "output_rate_limit": 10.0,  # 10 units per second max change
        "gain_schedule_enabled": True,
        "gain_schedule_points": [
            [0, 1.0, 1.0, 1.0],    # At PV=0: normal gains
            [50, 1.2, 0.8, 1.1],  # At PV=50: higher P, lower I
            [100, 0.8, 1.2, 0.9]  # At PV=100: lower P, higher I
        ]
    }
    
    # Create controller instance
    controller = AdvancedPIDController("example_pid", config)
    
    # Initialize and start
    controller.initialize()
    controller.start()
    
    # Simulate control loop
    import time
    
    controller.setpoint = 75.0  # Target temperature
    
    for i in range(10):
        # Simulate process variable (with some noise)
        import random
        controller.process_variable = 70.0 + i * 0.5 + random.uniform(-1, 1)
        
        # Execute control
        result = controller.execute()
        
        if result["success"]:
            stats = controller.get_advanced_stats()
            print(f"Step {i+1}: PV={controller.process_variable:.1f}, "
                  f"Output={controller._output:.1f}, "
                  f"Kp_eff={stats['effective_kp']:.2f}")
        
        time.sleep(0.1)
    
    # Stop controller
    controller.stop()
    
    print("Example completed successfully!")
