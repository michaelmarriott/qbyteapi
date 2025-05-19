import os
import numpy as np
import scipy.stats
import math
import matplotlib.pyplot as plt
from io import BytesIO

class QbyteDataProcessor:
    """Utility class for processing Qbyte data files"""
    
    def __init__(self, qbyte_dir):
        """Initialize with the path to Qbyte directory"""
        self.qbyte_dir = qbyte_dir
        self.shape_types = ['hypercube', 'sphere', 'pyramid', 'AEM', 'quad']
    
    def parse_file_header(self, file_path):
        """Parse the header information from a Qbyte file"""
        with open(file_path, 'r') as f:
            lines = f.read().split('\n')
        
        # Parse header
        header = lines[0].split(' ')
        params = {
            'ColorZ': float(header[1]) if len(header) > 1 else 1.65,
            'RotZ': float(header[3]) if len(header) > 3 else 1.85
        }
        
        # Parse RNG parameters
        if len(header) > 5:
            params['UseTrueRNG'] = header[5] == 'True'
            if len(header) > 6:
                params['HALO'] = header[6] == 'True'
            if len(header) > 7:
                params['TurboUse'] = header[7] == 'True'
        
        # Get first line to determine NEDspeed
        if len(lines) > 1:
            firstline = lines[1].split(',')
            params['NEDspeed'] = len(firstline) - 2
            params['TurboUse'] = firstline[-1] == 'T'
        
        return params, lines
    
    def calculate_statistics(self, params):
        """Calculate statistics based on parameters"""
        ColorZ = params.get('ColorZ', 1.65)
        RotZ = params.get('RotZ', 1.85)
        NEDspeed = params.get('NEDspeed', 250)
        
        # Calculate statistics
        ActionNumC = math.ceil((ColorZ*((8*NEDspeed*0.25)**0.5))+(4*NEDspeed))
        Pmod_Color = (scipy.stats.binom((NEDspeed*8), 0.5).sf(ActionNumC-1))*2
        ActionNumR = math.ceil((RotZ*((8*NEDspeed*0.25)**0.5))+(4*NEDspeed))
        Pmod_Rot = (scipy.stats.binom((NEDspeed*8), 0.5).sf(ActionNumR-1))*2
        
        return {
            'ActionNumC': ActionNumC,
            'Pmod_Color': Pmod_Color,
            'ActionNumR': ActionNumR,
            'Pmod_Rot': Pmod_Rot
        }
    
    def extract_qbyte_data(self, lines, limit=1000):
        """Extract QBYTE data from file lines"""
        qbyte_data = []
        timestamps = []
        
        for i, line in enumerate(lines[1:limit+1]):
            if 'QBYTE' in line:
                parts = line.split(',')
                if len(parts) > 2:
                    timestamp = int(parts[-2]) if parts[-2].isdigit() else 0
                    timestamps.append(timestamp)
                    
                    # Calculate bit sum for this line
                    bit_sum = 0
                    values = []
                    for val in parts[:-2]:
                        if val.isdigit():
                            values.append(int(val))
                            # Convert to binary and count 1s
                            bin_str = bin(256 + int(val))[3:]
                            bit_sum += sum(int(bit) for bit in bin_str)
                    
                    qbyte_data.append({
                        'timestamp': timestamp,
                        'bit_sum': bit_sum,
                        'values': values
                    })
        
        return qbyte_data, timestamps
    
    def count_events(self, lines):
        """Count different types of events in the file"""
        color_events = sum(1 for line in lines if 'color' in line)
        rotation_events = sum(1 for line in lines if 'rotation' in line)
        qbyte_lines = sum(1 for line in lines if 'QBYTE' in line)
        
        return {
            'color_events': color_events,
            'rotation_events': rotation_events,
            'qbyte_lines': qbyte_lines,
            'total_lines': len(lines)
        }
    
    def generate_visualization(self, file_path, limit=1000):
        """Generate visualization for a Qbyte file"""
        params, lines = self.parse_file_header(file_path)
        qbyte_data, timestamps = self.extract_qbyte_data(lines, limit)
        
        if not timestamps or not qbyte_data:
            return None
        
        # Create visualization
        plt.figure(figsize=(10, 6))
        plt.style.use('dark_background')
        
        # Convert timestamps to relative time in hours
        rel_times = [(t - timestamps[0])/3600000 for t in timestamps]
        
        # Extract bit sums
        bit_sums = [d['bit_sum'] for d in qbyte_data]
        
        # Plot the data
        plt.plot(rel_times, bit_sums, 'magenta', label='Qbyte Data')
        
        # Calculate and plot the cumulative sum
        cum_sum = np.cumsum(bit_sums)
        expected = np.arange(len(bit_sums)) * 4  # Assuming 8 bits per value, 0.5 expected probability
        plt.plot(rel_times, cum_sum - expected, 'cyan', label='Cumulative Deviation')
        
        # Add standard deviation lines
        std_dev = np.sqrt(np.arange(len(bit_sums)) * 4 * 0.25) * 1.96
        plt.plot(rel_times, std_dev, 'aqua', linestyle='--', label='+1.96σ')
        plt.plot(rel_times, -std_dev, 'aqua', linestyle='--', label='-1.96σ')
        
        plt.title(f'Qbyte Data Analysis: {os.path.basename(file_path)}')
        plt.xlabel('Time (hours)')
        plt.ylabel('Bit Count / Deviation')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Save to BytesIO object
        img_io = BytesIO()
        plt.savefig(img_io, format='png', bbox_inches='tight')
        img_io.seek(0)
        plt.close()
        
        return img_io
    
    def get_shape_data(self, shape_name, limit=1000):
        """Get data for a specific shape"""
        sim_file = f'sim_{shape_name}.txt'
        file_path = os.path.join(self.qbyte_dir, sim_file)
        
        if not os.path.exists(file_path):
            return None
        
        # Read shape data
        with open(file_path, 'r') as f:
            lines = f.read().split('\n')[:limit]
        
        values = [float(line) for line in lines if line.strip()]
        
        # Calculate basic statistics
        stats = {
            'count': len(values),
            'min': min(values) if values else None,
            'max': max(values) if values else None,
            'mean': np.mean(values) if values else None,
            'median': np.median(values) if values else None,
            'std': np.std(values) if values else None
        }
        
        return {
            'shape': shape_name,
            'statistics': stats,
            'data_sample': values[:100]  # Return only first 100 values
        }
    
    def get_hypercube_data(self):
        """Get hypercube data"""
        file_path = os.path.join(self.qbyte_dir, 'HypercubeExt.txt')
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            lines = f.read().split('\n')
        
        nodes = []
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4:
                    nodes.append({
                        'x': int(parts[0]) - 4,
                        'y': int(parts[1]) - 4,
                        'z': int(parts[2]) - 4,
                        'node': int(parts[3])
                    })
        
        return {
            'name': 'hypercube',
            'nodes': nodes,
            'total_nodes': len(nodes)
        }
