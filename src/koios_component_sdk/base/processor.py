"""
Base class for data processing components.

This module provides the ProcessorComponent base class for implementing data
processing algorithms in the Koios framework. Processor components handle
data transformation, filtering, analysis, and other data operations.
"""

from typing import Dict, Any, List, Optional, Union
from abc import abstractmethod
import time
from collections import deque

from .component import BaseKoiosComponent, ComponentMetadata, ParameterDefinition, ComponentStatus
from ..exceptions import ValidationError


class ProcessorComponent(BaseKoiosComponent):
    """
    Base class for data processing components.
    
    This class provides common functionality for data processing components
    including data buffering, batch processing, and result management.
    Processor components implement data transformation and analysis algorithms.
    """
    
    def __init__(self, component_id: str, parameters: Dict[str, Any]):
        """Initialize the processor component."""
        super().__init__(component_id, parameters)
        
        # Data buffers
        self._input_buffer: deque = deque(maxlen=parameters.get('buffer_size', 1000))
        self._output_buffer: deque = deque(maxlen=parameters.get('buffer_size', 1000))
        
        # Processing parameters
        self._batch_size: int = parameters.get('batch_size', 1)
        self._processing_interval: float = parameters.get('processing_interval', 1.0)
        self._last_processing_time: Optional[float] = None
        
        # Statistics
        self._processed_count: int = 0
        self._processing_time_total: float = 0.0
        self._last_processing_duration: float = 0.0
        self._error_count: int = 0
        
        # Results
        self._last_result: Optional[Any] = None
        self._result_history: deque = deque(maxlen=parameters.get('result_history_size', 100))
    
    @property
    def input_buffer_size(self) -> int:
        """Get current input buffer size."""
        return len(self._input_buffer)
    
    @property
    def output_buffer_size(self) -> int:
        """Get current output buffer size."""
        return len(self._output_buffer)
    
    @property
    def last_result(self) -> Optional[Any]:
        """Get the last processing result."""
        return self._last_result
    
    @property
    def processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        avg_processing_time = (self._processing_time_total / self._processed_count 
                             if self._processed_count > 0 else 0.0)
        
        return {
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "average_processing_time": avg_processing_time,
            "last_processing_duration": self._last_processing_duration,
            "input_buffer_size": self.input_buffer_size,
            "output_buffer_size": self.output_buffer_size,
            "result_history_size": len(self._result_history)
        }
    
    def get_bindable_fields(self) -> List[str]:
        """Return fields that can be bound to Koios tags."""
        return [
            "last_result",
            "processed_count",
            "error_count",
            "input_buffer_size",
            "output_buffer_size"
        ]
    
    @abstractmethod
    def process_data(self, data: List[Any]) -> Any:
        """
        Process input data.
        
        This method must be implemented by subclasses to define the specific
        data processing algorithm.
        
        Args:
            data: List of input data items to process
            
        Returns:
            Processing result
        """
        pass
    
    def add_input_data(self, data: Any) -> bool:
        """
        Add data to the input buffer.
        
        Args:
            data: Data item to add
            
        Returns:
            True if data was added successfully
        """
        try:
            self._input_buffer.append(data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to add input data: {str(e)}")
            return False
    
    def add_input_batch(self, data_list: List[Any]) -> int:
        """
        Add multiple data items to the input buffer.
        
        Args:
            data_list: List of data items to add
            
        Returns:
            Number of items successfully added
        """
        added_count = 0
        for data in data_list:
            if self.add_input_data(data):
                added_count += 1
        return added_count
    
    def get_input_data(self, count: int = 1) -> List[Any]:
        """
        Get data from the input buffer.
        
        Args:
            count: Number of items to retrieve
            
        Returns:
            List of data items
        """
        result = []
        for _ in range(min(count, len(self._input_buffer))):
            if self._input_buffer:
                result.append(self._input_buffer.popleft())
        return result
    
    def peek_input_data(self, count: int = 1) -> List[Any]:
        """
        Peek at data in the input buffer without removing it.
        
        Args:
            count: Number of items to peek at
            
        Returns:
            List of data items
        """
        return list(self._input_buffer)[:count]
    
    def clear_input_buffer(self):
        """Clear the input buffer."""
        self._input_buffer.clear()
        self.logger.debug("Input buffer cleared")
    
    def clear_output_buffer(self):
        """Clear the output buffer."""
        self._output_buffer.clear()
        self.logger.debug("Output buffer cleared")
    
    def get_result_history(self, count: Optional[int] = None) -> List[Any]:
        """
        Get processing result history.
        
        Args:
            count: Number of results to retrieve (None for all)
            
        Returns:
            List of historical results
        """
        if count is None:
            return list(self._result_history)
        else:
            return list(self._result_history)[-count:]
    
    def execute(self) -> Dict[str, Any]:
        """Execute data processing."""
        try:
            if self._status != ComponentStatus.RUNNING:
                return {
                    "success": False,
                    "error": f"Processor not running (status: {self._status.value})"
                }
            
            current_time = time.time()
            
            # Check if it's time to process
            if (self._last_processing_time is None or 
                current_time - self._last_processing_time >= self._processing_interval):
                
                # Check if we have enough data to process
                if len(self._input_buffer) >= self._batch_size:
                    
                    # Get data for processing
                    input_data = self.get_input_data(self._batch_size)
                    
                    # Process data and measure time
                    start_time = time.time()
                    try:
                        result = self.process_data(input_data)
                        
                        # Record successful processing
                        processing_duration = time.time() - start_time
                        self._last_processing_duration = processing_duration
                        self._processing_time_total += processing_duration
                        self._processed_count += 1
                        self._last_processing_time = current_time
                        
                        # Store result
                        self._last_result = result
                        self._result_history.append({
                            'timestamp': current_time,
                            'result': result,
                            'processing_duration': processing_duration
                        })
                        
                        # Add to output buffer if needed
                        self._output_buffer.append(result)
                        
                        self.logger.debug(f"Processed {len(input_data)} items in {processing_duration:.3f}s")
                        
                    except Exception as e:
                        self._error_count += 1
                        self.logger.error(f"Processing failed: {str(e)}")
                        raise
            
            # Record execution
            self._record_execution()
            
            return {
                "success": True,
                "last_result": self._last_result,
                "stats": self.processing_stats
            }
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_parameters(self) -> bool:
        """Validate processor parameters."""
        try:
            # Validate buffer size
            buffer_size = self.parameters.get('buffer_size', 1000)
            if not isinstance(buffer_size, int) or buffer_size < 1:
                raise ValidationError("buffer_size must be a positive integer", "buffer_size", "positive integer", buffer_size, self.component_id)
            
            # Validate batch size
            batch_size = self.parameters.get('batch_size', 1)
            if not isinstance(batch_size, int) or batch_size < 1:
                raise ValidationError("batch_size must be a positive integer", "batch_size", "positive integer", batch_size, self.component_id)
            
            # Validate processing interval
            processing_interval = self.parameters.get('processing_interval', 1.0)
            if not isinstance(processing_interval, (int, float)) or processing_interval <= 0:
                raise ValidationError("processing_interval must be a positive number", "processing_interval", "positive number", processing_interval, self.component_id)
            
            # Validate result history size
            result_history_size = self.parameters.get('result_history_size', 100)
            if not isinstance(result_history_size, int) or result_history_size < 1:
                raise ValidationError("result_history_size must be a positive integer", "result_history_size", "positive integer", result_history_size, self.component_id)
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Parameter validation failed: {str(e)}", component_id=self.component_id)
    
    def initialize(self) -> bool:
        """Initialize the processor."""
        try:
            self._set_status(ComponentStatus.INITIALIZING)
            
            # Set up processing parameters
            buffer_size = self.parameters.get('buffer_size', 1000)
            self._input_buffer = deque(maxlen=buffer_size)
            self._output_buffer = deque(maxlen=buffer_size)
            
            self._batch_size = self.parameters.get('batch_size', 1)
            self._processing_interval = self.parameters.get('processing_interval', 1.0)
            
            result_history_size = self.parameters.get('result_history_size', 100)
            self._result_history = deque(maxlen=result_history_size)
            
            # Reset statistics
            self._processed_count = 0
            self._processing_time_total = 0.0
            self._last_processing_duration = 0.0
            self._error_count = 0
            self._last_processing_time = None
            self._last_result = None
            
            self._set_status(ComponentStatus.INITIALIZED)
            self.logger.info("Processor initialized successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
    
    def start(self) -> bool:
        """Start the processor."""
        try:
            if self._status != ComponentStatus.INITIALIZED:
                raise ValueError(f"Cannot start from status {self._status.value}")
            
            self._set_status(ComponentStatus.STARTING)
            
            # Clear buffers
            self.clear_input_buffer()
            self.clear_output_buffer()
            
            self._set_status(ComponentStatus.RUNNING)
            self.logger.info("Processor started successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
    
    def stop(self) -> bool:
        """Stop the processor."""
        try:
            self._set_status(ComponentStatus.STOPPING)
            
            # Process any remaining data if configured
            if self.parameters.get('process_remaining_on_stop', False):
                while len(self._input_buffer) > 0:
                    input_data = self.get_input_data(min(self._batch_size, len(self._input_buffer)))
                    try:
                        result = self.process_data(input_data)
                        self._output_buffer.append(result)
                        self.logger.info(f"Processed {len(input_data)} remaining items on stop")
                    except Exception as e:
                        self.logger.error(f"Failed to process remaining data: {str(e)}")
                        break
            
            self._set_status(ComponentStatus.STOPPED)
            self.logger.info("Processor stopped successfully")
            return True
            
        except Exception as e:
            self._set_status(ComponentStatus.ERROR, str(e))
            return False
