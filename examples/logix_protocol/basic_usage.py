"""
Basic Usage Example for Logix Protocol Component

This script demonstrates basic connection, reading, and writing operations
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


def basic_read_example():
    """Demonstrate basic reading from PLC."""
    print("\n" + "="*70)
    print("Basic Read Example")
    print("="*70)
    
    # Configuration
    config = {
        "host": "192.168.1.100",
        "controller_slot": 0,
        "timeout": 5.0,
        "tags": [
            {
                "name": "temperature",
                "address": "Temperature_PV",
                "data_type": LogixDataType.REAL,
                "writable": False
            },
            {
                "name": "pressure",
                "address": "Pressure_PV",
                "data_type": LogixDataType.REAL,
                "writable": False
            },
            {
                "name": "pump_running",
                "address": "Pump_01_Running",
                "data_type": LogixDataType.BOOLEAN,
                "writable": False
            }
        ]
    }
    
    # Create component
    component = LogixProtocolComponent("basic_read", config)
    
    try:
        # Initialize component
        if not component.initialize():
            print("✗ Failed to initialize component")
            return
        print("✓ Component initialized")
        
        # Start component (establishes connection)
        if not component.start():
            print("✗ Failed to start component")
            return
        print("✓ Component started and connected")
        
        # Read all tags
        print("\nReading tags...")
        values = component.read_all_tags()
        
        # Display results
        for tag_name, value in values.items():
            tag_info = component.get_tag_info(tag_name)
            print(f"  {tag_name:20s}: {value:>10} (Quality: {tag_info['quality']})")
        
        # Get statistics
        stats = component.get_statistics()
        print(f"\nStatistics:")
        print(f"  Successful reads: {stats['reads']['successful']}")
        print(f"  Failed reads: {stats['reads']['failed']}")
        
    except Exception as e:
        logger.error(f"Error in basic read example: {e}")
    
    finally:
        # Clean up
        component.stop()
        print("\n✓ Component stopped")


def basic_write_example():
    """Demonstrate basic writing to PLC."""
    print("\n" + "="*70)
    print("Basic Write Example")
    print("="*70)
    
    # Configuration with writable tags
    config = {
        "host": "192.168.1.100",
        "controller_slot": 0,
        "timeout": 5.0,
        "tags": [
            {
                "name": "setpoint",
                "address": "Temperature_SP",
                "data_type": LogixDataType.REAL,
                "writable": True
            },
            {
                "name": "valve_position",
                "address": "Valve_01_Position",
                "data_type": LogixDataType.INTEGER,
                "writable": True
            },
            {
                "name": "enable_flag",
                "address": "System_Enable",
                "data_type": LogixDataType.BOOLEAN,
                "writable": True
            }
        ]
    }
    
    # Create component
    component = LogixProtocolComponent("basic_write", config)
    
    try:
        # Initialize and start
        if not component.initialize():
            print("✗ Failed to initialize component")
            return
        print("✓ Component initialized")
        
        if not component.start():
            print("✗ Failed to start component")
            return
        print("✓ Component started and connected")
        
        # Write values to tags
        print("\nWriting tags...")
        write_values = {
            "setpoint": 75.5,
            "valve_position": 50,
            "enable_flag": True
        }
        
        for tag_name, value in write_values.items():
            print(f"  {tag_name}: {value}")
        
        success = component.write_tags(write_values)
        
        if success:
            print("✓ All writes successful")
        else:
            print("✗ Some writes failed")
        
        # Read back to verify
        print("\nReading back values...")
        time.sleep(0.1)  # Small delay to allow PLC to update
        read_values = component.read_all_tags()
        
        for tag_name, value in read_values.items():
            print(f"  {tag_name}: {value}")
        
        # Get statistics
        stats = component.get_statistics()
        print(f"\nStatistics:")
        print(f"  Successful writes: {stats['writes']['successful']}")
        print(f"  Failed writes: {stats['writes']['failed']}")
        
    except Exception as e:
        logger.error(f"Error in basic write example: {e}")
    
    finally:
        # Clean up
        component.stop()
        print("\n✓ Component stopped")


def monitoring_example():
    """Demonstrate continuous monitoring with health checks."""
    print("\n" + "="*70)
    print("Monitoring Example")
    print("="*70)
    
    # Configuration
    config = {
        "host": "192.168.1.100",
        "controller_slot": 0,
        "health_check_interval": 10.0,
        "tags": [
            {
                "name": "temperature",
                "address": "Temperature_PV",
                "data_type": LogixDataType.REAL,
                "writable": False
            },
            {
                "name": "pressure",
                "address": "Pressure_PV",
                "data_type": LogixDataType.REAL,
                "writable": False
            }
        ]
    }
    
    # Create component
    component = LogixProtocolComponent("monitoring", config)
    
    try:
        # Initialize and start
        if not component.initialize():
            print("✗ Failed to initialize component")
            return
        print("✓ Component initialized")
        
        if not component.start():
            print("✗ Failed to start component")
            return
        print("✓ Component started and connected")
        
        # Monitor for 30 seconds
        print("\nMonitoring (30 seconds)...")
        print("Press Ctrl+C to stop early\n")
        
        start_time = time.time()
        last_health_check = 0
        
        while time.time() - start_time < 30:
            # Read tags
            values = component.read_all_tags()
            
            # Display current values
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] ", end="")
            for tag_name, value in values.items():
                print(f"{tag_name}={value:.2f}  ", end="")
            print()
            
            # Periodic health check
            if time.time() - last_health_check > 10:
                health = component.health_check()
                print(f"  Health: {health['status']} - {health['message']}")
                last_health_check = time.time()
            
            # Wait before next read
            time.sleep(2)
        
        # Final statistics
        print("\nFinal Statistics:")
        stats = component.get_statistics()
        print(f"  Connection time: {stats['connection']['connection_time']:.2f}s")
        print(f"  Successful reads: {stats['reads']['successful']}")
        print(f"  Failed reads: {stats['reads']['failed']}")
        
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    
    except Exception as e:
        logger.error(f"Error in monitoring example: {e}")
    
    finally:
        # Clean up
        component.stop()
        print("\n✓ Component stopped")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("Logix Protocol Component - Basic Usage Examples")
    print("="*70)
    
    print("\nNote: Update the 'host' and tag addresses in the examples")
    print("      to match your PLC configuration.\n")
    
    # Run examples
    try:
        # Example 1: Basic reading
        basic_read_example()
        
        # Wait between examples
        time.sleep(2)
        
        # Example 2: Basic writing
        basic_write_example()
        
        # Wait between examples
        time.sleep(2)
        
        # Example 3: Monitoring
        monitoring_example()
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
    
    print("\n" + "="*70)
    print("Examples completed")
    print("="*70)


if __name__ == "__main__":
    main()

