"""
Headless version of QByte.py for API usage
This version removes GUI dependencies and focuses on data generation
"""
import os
import sys
import time
import math
import numpy as np
import scipy.stats
import json
from datetime import datetime, timedelta

# Add the Qbyte directory to the path
QBYTE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Qbyte')
sys.path.append(QBYTE_DIR)

class QByteHeadless:
    def __init__(self, mode='static', remarks='API'):
        self.mode = mode
        self.remarks = remarks
        self.outpath = QBYTE_DIR
        
        # Default parameters (same as in original QByte.py)
        self.ColorZ = 1.65
        self.RotZ = 1.85
        self.NEDspeed = 250
        self.UseTrueRNG = False
        self.HALO = True
        self.TurboUse = False
        
        # Initialize data structures
        self.qbyte_data = []
        self.timestamps = []
        self.events = {
            'color_events': 0,
            'rotation_events': 0,
            'qbyte_lines': 0
        }
        
        # Setup output files
        self.starttime = int(time.time()*1000)
        self.outfile_path = f'{self.outpath}/QB_{int(self.starttime/1000)}_{self.remarks}.txt'
        self.cmtfile_path = f'{self.outpath}/QB_{int(self.starttime/1000)}_{self.remarks}_C.txt'
        
        # Create output files
        with open(self.outfile_path, 'w') as outfile:
            outfile.write(f'ColorZ: {self.ColorZ} RotZ: {self.RotZ} RNG params: {self.UseTrueRNG} {self.HALO} {self.TurboUse}\n')
        
        # Calculate statistics
        self.EX = self.NEDspeed * 4
        self.ColorThres = self.ColorZ * ((self.NEDspeed*8*0.25)**0.5)
        self.RotThres = self.RotZ * ((self.NEDspeed*8*0.25)**0.5)
        
        self.ActionNumC = math.ceil((self.ColorZ*((8*self.NEDspeed*0.25)**0.5))+(4*self.NEDspeed))
        self.Pmod_Color = (scipy.stats.binom((self.NEDspeed*8), 0.5).sf(self.ActionNumC-1))*2
        self.ActionNumR = math.ceil((self.RotZ*((8*self.NEDspeed*0.25)**0.5))+(4*self.NEDspeed))
        self.Pmod_Rot = (scipy.stats.binom((self.NEDspeed*8), 0.5).sf(self.ActionNumR-1))*2
        
        print(f"Initialized QByte in headless mode with {self.mode} mode and remarks: {self.remarks}")
        print(f"Output files: {self.outfile_path} and {self.cmtfile_path}")
        print(f"Statistics: ActionNumC={self.ActionNumC}, Pmod_Color={self.Pmod_Color}")
        print(f"Statistics: ActionNumR={self.ActionNumR}, Pmod_Rot={self.Pmod_Rot}")
    
    def generate_bulk_data(self, num_iterations=60):
        """Generate bulk data (similar to the Bulk() function in original QByte.py)"""
        print(f"Generating {num_iterations} iterations of bulk data...")
        
        for i in range(num_iterations):
            timestamp = int(time.time()*1000)
            self.timestamps.append(timestamp)
            
            # Generate random data (simulating RNG hardware)
            values = np.random.randint(0, 256, size=self.NEDspeed).tolist()
            
            # Calculate bit sum
            bit_sum = 0
            for val in values:
                bin_str = bin(256 + val)[3:]
                bit_sum += sum(int(bit) for bit in bin_str)
            
            # Create QBYTE line
            qbyte_line = f"QBYTE,{','.join(map(str, values))},{timestamp},{'T' if self.TurboUse else 'F'}"
            
            # Write to output file
            with open(self.outfile_path, 'a') as outfile:
                outfile.write(qbyte_line + '\n')
            
            # Store data
            self.qbyte_data.append({
                'timestamp': timestamp,
                'bit_sum': bit_sum,
                'values': values
            })
            
            # Generate events based on thresholds
            if bit_sum > self.ActionNumC:
                self.events['color_events'] += 1
                color_event = f"color,{timestamp}"
                with open(self.outfile_path, 'a') as outfile:
                    outfile.write(color_event + '\n')
            
            if bit_sum > self.ActionNumR:
                self.events['rotation_events'] += 1
                rotation_event = f"rotation,{timestamp}"
                with open(self.outfile_path, 'a') as outfile:
                    outfile.write(rotation_event + '\n')
            
            self.events['qbyte_lines'] += 1
            
            # Print progress
            if i % 10 == 0:
                print(f"Generated {i}/{num_iterations} iterations. Current bit sum: {bit_sum}")
            
            # Sleep to simulate real-time generation
            time.sleep(0.1)
        
        return self.get_results()
    
    def generate_continuous_data(self):
        """Generate data continuously, yielding results after each iteration"""
        print("Starting continuous data generation...")
        
        i = 0
        try:
            while True:
                timestamp = int(time.time()*1000)
                self.timestamps.append(timestamp)
                
                # Generate random data (simulating RNG hardware)
                values = np.random.randint(0, 256, size=self.NEDspeed).tolist()
                
                # Calculate bit sum
                bit_sum = 0
                for val in values:
                    bin_str = bin(256 + val)[3:]
                    bit_sum += sum(int(bit) for bit in bin_str)
                
                # Create QBYTE line
                qbyte_line = f"QBYTE,{','.join(map(str, values))},{timestamp},{'T' if self.TurboUse else 'F'}"
                
                # Write to output file
                with open(self.outfile_path, 'a') as outfile:
                    outfile.write(qbyte_line + '\n')
                
                # Store data
                self.qbyte_data.append({
                    'timestamp': timestamp,
                    'bit_sum': bit_sum,
                    'values': values
                })
                
                # Generate events based on thresholds
                events_this_iteration = []
                
                if bit_sum > self.ActionNumC:
                    self.events['color_events'] += 1
                    color_event = f"color,{timestamp}"
                    with open(self.outfile_path, 'a') as outfile:
                        outfile.write(color_event + '\n')
                    events_this_iteration.append({"type": "color", "timestamp": timestamp})
                
                if bit_sum > self.ActionNumR:
                    self.events['rotation_events'] += 1
                    rotation_event = f"rotation,{timestamp}"
                    with open(self.outfile_path, 'a') as outfile:
                        outfile.write(rotation_event + '\n')
                    events_this_iteration.append({"type": "rotation", "timestamp": timestamp})
                
                self.events['qbyte_lines'] += 1
                
                # Create iteration result
                iteration_result = {
                    'iteration': i,
                    'timestamp': timestamp,
                    'bit_sum': bit_sum,
                    'events': events_this_iteration,
                    'values': values[:10]  # Only include first 10 values to keep response size reasonable
                }
                
                # Print progress periodically
                if i % 10 == 0:
                    print(f"Generated iteration {i}. Current bit sum: {bit_sum}")
                
                i += 1
                
                # Sleep to simulate real-time generation
                time.sleep(0.1)
                
                # Yield the current iteration result
                yield iteration_result
                
        except GeneratorExit:
            print("Generator closed after", i, "iterations")
    
    def get_results(self):
        """Get the results of the generation"""
        # Calculate statistics
        bit_sums = [d['bit_sum'] for d in self.qbyte_data]
        cum_sum = np.cumsum(bit_sums)
        expected = np.arange(len(bit_sums)) * 4
        deviation = cum_sum - expected
        
        # Calculate standard deviation lines
        std_dev = np.sqrt(np.arange(len(bit_sums)) * 4 * 0.25) * 1.96
        
        results = {
            'file_info': {
                'outfile': self.outfile_path,
                'cmtfile': self.cmtfile_path,
                'starttime': self.starttime
            },
            'parameters': {
                'ColorZ': self.ColorZ,
                'RotZ': self.RotZ,
                'NEDspeed': self.NEDspeed,
                'UseTrueRNG': self.UseTrueRNG,
                'HALO': self.HALO,
                'TurboUse': self.TurboUse
            },
            'statistics': {
                'ActionNumC': self.ActionNumC,
                'Pmod_Color': self.Pmod_Color,
                'ActionNumR': self.ActionNumR,
                'Pmod_Rot': self.Pmod_Rot
            },
            'events': self.events,
            'data_summary': {
                'total_iterations': len(self.qbyte_data),
                'bit_sums': bit_sums,
                'cumulative_deviation': deviation.tolist(),
                'std_dev': std_dev.tolist()
            }
        }
        
        return results

def run_qbyte(mode='static', remarks='API', iterations=60):
    """Run QByte in headless mode and return results"""
    qbyte = QByteHeadless(mode, remarks)
    return qbyte.generate_bulk_data(iterations)

if __name__ == '__main__':
    # If run directly, parse command line arguments
    mode = sys.argv[1] if len(sys.argv) > 1 else 'static'
    remarks = sys.argv[2] if len(sys.argv) > 2 else 'API'
    iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    results = run_qbyte(mode, remarks, iterations)
    print(json.dumps(results, indent=2))
