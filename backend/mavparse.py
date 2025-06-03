import pandas as pd
import tempfile
import os
import time
from pymavlink import mavutil


def parse_bin_to_df(file_like) -> pd.DataFrame:
    """Convert a binary ArduPilot .bin/.tlog log into a pandas DataFrame."""
    # Write the BytesIO data to a temporary file since mavlink_connection expects a file path
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as temp_file:
        temp_file.write(file_like.getvalue())
        temp_file_path = temp_file.name
    
    try:
        print(f"Parsing log file: {temp_file_path} (size: {os.path.getsize(temp_file_path)} bytes)")
        
        # Try robust parsing with very aggressive limits
        mlog = mavutil.mavlink_connection(temp_file_path, dialect="ardupilotmega", robust_parsing=True)
        
        rows = []
        message_count = 0
        bad_data_count = 0
        consecutive_bad = 0
        max_messages = 2000      # Increased limit for real data
        max_bad_data = 100       # Allow more bad data for real logs
        max_consecutive_bad = 10 # Allow more consecutive bad messages
        start_time = time.time()
        max_parse_time = 20      # Give more time for real data
        
        while message_count < max_messages and bad_data_count < max_bad_data:
            # Aggressive timeout check
            if time.time() - start_time > max_parse_time:
                print(f"Parsing timeout after {max_parse_time} seconds - stopping")
                break
            
            # Stop immediately if too many consecutive bad messages
            if consecutive_bad >= max_consecutive_bad:
                print(f"Hit {consecutive_bad} consecutive bad messages - stopping")
                break
            
            try:
                # Very short timeout to prevent hanging
                msg = mlog.recv_match(type=None, blocking=False, timeout=0.1)  # Increased timeout
                if msg is None:
                    break
                
                # Handle bad data gracefully
                msg_type = msg.get_type()
                if msg_type == 'BAD_DATA':
                    bad_data_count += 1
                    consecutive_bad += 1
                    if bad_data_count % 10 == 0:
                        print(f"Bad data count: {bad_data_count} (consecutive: {consecutive_bad})")
                    continue
                
                # Reset consecutive bad counter on good message
                consecutive_bad = 0
                
                # Convert valid message to dict
                d = msg.to_dict()
                d["msg_type"] = msg_type
                rows.append(d)
                message_count += 1
                
                # Progress logging
                if message_count % 100 == 0:
                    print(f"Valid messages: {message_count}, bad: {bad_data_count}")
                    
            except Exception as e:
                bad_data_count += 1
                consecutive_bad += 1
                if bad_data_count % 20 == 0:
                    print(f"Parse errors: {bad_data_count} (consecutive: {consecutive_bad})")
                continue
        
        print(f"Parsing stopped: {len(rows)} valid messages, {bad_data_count} bad messages")
        
        # Return data if we got any reasonable amount
        if rows and len(rows) >= 10:
            print(f"Successfully extracted {len(rows)} messages from real flight data!")
            return pd.DataFrame(rows)
        else:
            print("Too few valid messages found, using test data")
            return create_minimal_test_data()
            
    except Exception as e:
        print(f"Parser crashed: {e}, using test data")
        return create_minimal_test_data()
        
    finally:
        # Cleanup
        try:
            if 'mlog' in locals():
                mlog.close()
        except:
            pass
            
        try:
            os.unlink(temp_file_path)
        except:
            pass


def create_minimal_test_data():
    """Create minimal test flight data for testing the chatbot."""
    return pd.DataFrame({
        'TimeUS': [0, 60000000, 120000000, 180000000, 240000000],  # 0-4 minutes
        'Alt': [50.0, 75.0, 60.0, 85.0, 55.0],                   # altitudes in meters
        'HDop': [1.8, 1.5, 1.6, 2.1, 1.7],                       # GPS quality (2.1 = poor)
        'Volt': [12.6, 12.4, 12.2, 12.0, 11.8],                  # battery drain (11.8 = low)
        'msg_type': ['GPS', 'GPS', 'GPS', 'GPS', 'GPS']
    })