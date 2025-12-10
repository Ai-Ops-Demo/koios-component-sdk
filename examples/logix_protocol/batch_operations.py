"""
Batch Operations Example for Logix Protocol Component

This script demonstrates efficient batch reading and writing operations
with an Allen-Bradley Logix PLC.
"""

import logging
import time
from component import LogixProtocolComponent, LogixDataType

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def batch_read_performance_test():
    """Compare performance of batch vs. individual reads."""
    print("\n" + "="*70)
    print("Batch Read Performance Test")
    print("="*70)
    
    # Configuration with multiple tags
    num_tags = 20
    config = {
        "host": "192.168.1.100",
        "controller_slot": 0,
        "timeout": 10.0,
        "read_batch_size": num_tags,
        "tags": [
            {
                "name": f"tag_{i:02d}",
                "address": f"TestArray[{i}]",
                "data_type": LogixDataType.REAL,
                "writable": False
            }
            for i in range(num_tags)
        ]
    }
    
    # Create component
    component = LogixProtocolComponent("batch_perf", config)
    
    try:
        # Initialize and start
        if not component.initialize() or not component.start():
            print("✗ Failed to initialize/start component")
            return
        print(f"✓ Component started with {num_tags} tags configured")
        
        # Test batch read
        print(f"\nBatch reading {num_tags} tags...")
        start_time = time.time()
        values = component.read_all_tags()
        batch_time = time.time() - start_time
        
        print(f"  Time: {batch_time:.3f}s")
        print(f"  Tags read: {len(values)}")
        print(f"  Average time per tag: {batch_time/num_tags*1000:.1f}ms")
        
        # Display sample values
        print(f"\nSample values (first 5):")
        for i, (tag_name, value) in enumerate(list(values.items())[:5]):
            print(f"  {tag_name}: {value}")
        
        # Get statistics
        stats = component.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total reads: {stats['reads']['successful']}")
        print(f"  Read duration: {stats['reads']['last_duration']:.3f}s")
        
    except Exception as e:
        logger.error(f"Error in batch performance test: {e}")
    
    finally:
        component.stop()
        print("\n✓ Component stopped")


def batch_write_example():
    """Demonstrate batch writing multiple tags."""
    print("\n" + "="*70)
    print("Batch Write Example")
    print("="*70)
    
    # Configuration with writable tags
    config = {
        "host": "192.168.1.100",
        "controller_slot": 0,
        "timeout": 10.0,
        "write_batch_size": 10,
        "tags": [
            {
                "name": f"output_{i:02d}",
                "address": f"OutputArray[{i}]",
                "data_type": LogixDataType.REAL,
                "writable": True
            }
            for i in range(10)
        ]
    }
    
    # Create component
    component = LogixProtocolComponent("batch_write", config)
    
    try:
        # Initialize and start
        if not component.initialize() or not component.start():
            print("✗ Failed to initialize/start component")
            return
        print("✓ Component started")
        
        # Prepare batch write data
        write_values = {
            f"output_{i:02d}": float(i * 10)
            for i in range(10)
        }
        
        print(f"\nWriting {len(write_values)} tags in batch...")
        for tag_name, value in list(write_values.items())[:5]:
            print(f"  {tag_name}: {value}")
        print(f"  ... and {len(write_values) - 5} more")
        
        # Perform batch write
        start_time = time.time()
        success = component.write_tags(write_values)
        write_time = time.time() - start_time
        
        if success:
            print(f"✓ Batch write successful in {write_time:.3f}s")
        else:
            print(f"✗ Batch write failed")
        
        # Verify by reading back
        print(f"\nVerifying written values...")
        time.sleep(0.1)
        read_values = component.read_all_tags()
        
        # Compare written vs. read values
        mismatches = 0
        for tag_name, written_value in write_values.items():
            read_value = read_values.get(tag_name)
            if read_value is not None:
                if abs(read_value - written_value) > 0.01:
                    print(f"  ⚠ {tag_name}: wrote {written_value}, read {read_value}")
                    mismatches += 1
        
        if mismatches == 0:
            print(f"✓ All {len(write_values)} values verified successfully")
        else:
            print(f"⚠ {mismatches} value mismatches detected")
        
        # Get statistics
        stats = component.get_statistics()
        print(f"\nStatistics:")
        print(f"  Successful writes: {stats['writes']['successful']}")
        print(f"  Failed writes: {stats['writes']['failed']}")
        print(f"  Write duration: {stats['writes']['last_duration']:.3f}s")
        
    except Exception as e:
        logger.error(f"Error in batch write example: {e}")
    
    finally:
        component.stop()
        print("\n✓ Component stopped")


def mixed_batch_operations():
    """Demonstrate mixed read/write operations in batches."""
    print("\n" + "="*70)
    print("Mixed Batch Operations Example")
    print("="*70)
    
    # Configuration with mixed tags
    config = {
        "host": "192.168.1.100",
        "controller_slot": 0,
        "timeout": 10.0,
        "tags": [
            # Input tags (read-only)
            {
                "name": "sensor_temp",
                "address": "Sensor_Temperature",
                "data_type": LogixDataType.REAL,
                "writable": False
            },
            {
                "name": "sensor_pressure",
                "address": "Sensor_Pressure",
                "data_type": LogixDataType.REAL,
                "writable": False
            },
            {
                "name": "sensor_flow",
                "address": "Sensor_Flow",
                "data_type": LogixDataType.REAL,
                "writable": False
            },
            # Output tags (writable)
            {
                "name": "actuator_valve",
                "address": "Actuator_Valve_Position",
                "data_type": LogixDataType.REAL,
                "writable": True
            },
            {
                "name": "actuator_pump",
                "address": "Actuator_Pump_Speed",
                "data_type": LogixDataType.REAL,
                "writable": True
            },
            # Status tags (read-only)
            {
                "name": "status_running",
                "address": "System_Running",
                "data_type": LogixDataType.BOOLEAN,
                "writable": False
            },
            {
                "name": "status_alarm",
                "address": "System_Alarm",
                "data_type": LogixDataType.BOOLEAN,
                "writable": False
            }
        ]
    }
    
    # Create component
    component = LogixProtocolComponent("mixed_ops", config)
    
    try:
        # Initialize and start
        if not component.initialize() or not component.start():
            print("✗ Failed to initialize/start component")
            return
        print("✓ Component started")
        
        # Simulate control loop with read-process-write cycle
        print("\nRunning control loop (5 iterations)...")
        
        for iteration in range(5):
            print(f"\nIteration {iteration + 1}:")
            
            # Step 1: Read all inputs
            print("  1. Reading sensors...")
            values = component.read_all_tags()
            
            sensor_temp = values.get('sensor_temp', 0)
            sensor_pressure = values.get('sensor_pressure', 0)
            sensor_flow = values.get('sensor_flow', 0)
            
            print(f"     Temperature: {sensor_temp:.2f}")
            print(f"     Pressure: {sensor_pressure:.2f}")
            print(f"     Flow: {sensor_flow:.2f}")
            
            # Step 2: Simple control logic
            print("  2. Calculating outputs...")
            
            # Simple proportional control
            target_temp = 75.0
            temp_error = target_temp - sensor_temp
            valve_position = 50.0 + (temp_error * 2.0)  # P control
            valve_position = max(0.0, min(100.0, valve_position))  # Clamp 0-100
            
            # Flow-based pump speed
            target_flow = 100.0
            flow_error = target_flow - sensor_flow
            pump_speed = 50.0 + (flow_error * 0.5)
            pump_speed = max(0.0, min(100.0, pump_speed))
            
            print(f"     Valve position: {valve_position:.2f}%")
            print(f"     Pump speed: {pump_speed:.2f}%")
            
            # Step 3: Write outputs
            print("  3. Writing actuators...")
            write_success = component.write_tags({
                'actuator_valve': valve_position,
                'actuator_pump': pump_speed
            })
            
            if write_success:
                print("     ✓ Outputs written successfully")
            else:
                print("     ✗ Output write failed")
            
            # Step 4: Check status
            status_running = values.get('status_running', False)
            status_alarm = values.get('status_alarm', False)
            
            if status_alarm:
                print("     ⚠ ALARM CONDITION")
            
            if not status_running:
                print("     ⚠ System not running")
            
            # Wait before next iteration
            time.sleep(1)
        
        # Final statistics
        print("\nFinal Statistics:")
        stats = component.get_statistics()
        print(f"  Total reads: {stats['reads']['successful']}")
        print(f"  Total writes: {stats['writes']['successful']}")
        print(f"  Total errors: {stats['reads']['failed'] + stats['writes']['failed']}")
        
    except Exception as e:
        logger.error(f"Error in mixed operations example: {e}")
    
    finally:
        component.stop()
        print("\n✓ Component stopped")


def main():
    """Run all batch operation examples."""
    print("\n" + "="*70)
    print("Logix Protocol Component - Batch Operations Examples")
    print("="*70)
    
    print("\nNote: Update the 'host' and tag addresses in the examples")
    print("      to match your PLC configuration.\n")
    
    # Run examples
    try:
        # Example 1: Batch read performance
        batch_read_performance_test()
        
        time.sleep(2)
        
        # Example 2: Batch write
        batch_write_example()
        
        time.sleep(2)
        
        # Example 3: Mixed operations
        mixed_batch_operations()
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
    
    print("\n" + "="*70)
    print("Examples completed")
    print("="*70)


if __name__ == "__main__":
    main()

