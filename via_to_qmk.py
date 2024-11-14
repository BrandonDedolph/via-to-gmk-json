#!/usr/bin/env python3
"""
VIA to QMK layout converter with enhanced 60% keyboard layout detection.
Supports various 60% layouts including Nuphy Air 60 v2 style (ANSI with split right shift).
"""

import json
import argparse
from typing import List, Dict, Union, Tuple, Optional

class LayoutAnalyzer:
    """Analyzes keyboard layouts and detects their type."""
    
    @staticmethod
    def get_matrix_positions(layout: List[Union[str, Dict]]) -> List[str]:
        """Extract matrix positions from VIA layout."""
        matrix_positions = []
        for key in layout:
            if isinstance(key, str):
                matrix_positions.append(key)
            elif isinstance(key, dict):
                matrix = next((v for k, v in key.items() if ',' in str(v)), None)
                if matrix:
                    matrix_positions.append(matrix)
        return matrix_positions

    @staticmethod
    def analyze_layout_properties(layout_data: List[Union[str, Dict]]) -> Dict:
        """
        Analyze layout properties to determine specific features.
        Returns a dictionary containing detailed layout characteristics.
        """
        properties = {
            'total_keys': len(LayoutAnalyzer.get_matrix_positions(layout_data)),
            'key_widths': [],
            'split_backspace': False,
            'split_right_shift': False,
            'split_left_shift': False,
            'has_standard_backspace': False,
            'has_ansi_enter': False,
            'bottom_row': {
                'left_mods': 0,
                'space': 0,
                'right_mods': 0,
                'is_standard_wk': False,
                'is_tsangan': False,
                'is_hhkb': False,
                'has_blockers': False
            },
            'blockers': [],
            'row_data': []
        }
        
        current_row = 0
        x_position = 0
        current_row_data = []
        
        for key in layout_data:
            width = 1
            x = 0
            y = 0
            
            if isinstance(key, dict):
                width = key.get('w', 1)
                x = key.get('x', 0)
                y = key.get('y', 0)
                
                if y > current_row:
                    properties['row_data'].append(current_row_data)
                    current_row_data = []
                    current_row = y
                    x_position = 0
                
                # Track key properties
                properties['key_widths'].append(width)
                current_row_data.append({
                    'x': x_position,
                    'width': width,
                    'is_blocker': key.get('d', False)
                })
                
                # Detect key features
                if current_row == 0:  # First row (backspace)
                    if x_position in [13, 14] and width == 1:
                        properties['split_backspace'] = True
                    elif x_position == 13 and width == 2:
                        properties['has_standard_backspace'] = True
                
                elif current_row == 2:  # Third row (enter)
                    if x_position == 13 and width == 2:
                        properties['has_ansi_enter'] = True
                
                elif current_row == 3:  # Fourth row (shifts)
                    if x_position == 0 and width == 1.25:
                        properties['split_left_shift'] = True
                    elif x_position == 13:
                        if width == 1.75 or width == 1:
                            properties['split_right_shift'] = True
                
                elif current_row == 4:  # Bottom row
                    if key.get('d', False):  # Blocker detection
                        properties['blockers'].append((x, y))
                        properties['bottom_row']['has_blockers'] = True
                    
                    if x_position < 5:  # Left mods
                        properties['bottom_row']['left_mods'] += width
                    elif 5 <= x_position <= 9:  # Spacebar
                        properties['bottom_row']['space'] = max(
                            properties['bottom_row']['space'], width
                        )
                    else:  # Right mods
                        properties['bottom_row']['right_mods'] += width
                
                x_position += width
            else:
                x_position += 1
                properties['key_widths'].append(1)
                current_row_data.append({
                    'x': x_position,
                    'width': 1,
                    'is_blocker': False
                })
        
        # Add the last row
        if current_row_data:
            properties['row_data'].append(current_row_data)
        
        # Detect bottom row layout
        if (abs(properties['bottom_row']['left_mods'] - 3.75) < 0.1 and  # 3x 1.25u
            abs(properties['bottom_row']['space'] - 6.25) < 0.1 and      # 6.25u
            abs(properties['bottom_row']['right_mods'] - 5) < 0.1):      # 4x 1.25u
            properties['bottom_row']['is_standard_wk'] = True
        
        elif (abs(properties['bottom_row']['left_mods'] - 3) < 0.1 and   # 3x 1u
              abs(properties['bottom_row']['space'] - 7) < 0.1 and       # 7u
              abs(properties['bottom_row']['right_mods'] - 3) < 0.1):    # 3x 1u
            properties['bottom_row']['is_tsangan'] = True
        
        elif (properties['bottom_row']['has_blockers'] and
              abs(properties['bottom_row']['space'] - 6) < 0.1):         # 6u
            properties['bottom_row']['is_hhkb'] = True
        
        return properties

    @staticmethod
    def detect_layout_type(layout_data: List[Union[str, Dict]]) -> str:
        """
        Detect the keyboard layout type based on comprehensive analysis.
        Returns the QMK layout identifier string.
        """
        props = LayoutAnalyzer.analyze_layout_properties(layout_data)
        
        # Nuphy Air 60 v2 style (ANSI with split right shift)
        if (props['total_keys'] == 62 and
            props['has_standard_backspace'] and
            props['has_ansi_enter'] and
            props['split_right_shift'] and
            not props['split_backspace'] and
            not props['split_left_shift'] and
            props['bottom_row']['is_standard_wk']):
            return "LAYOUT_60_ansi_split_rshift"
        
        # HHKB Layout
        if (props['total_keys'] == 60 and
            props['split_backspace'] and
            props['bottom_row']['is_hhkb'] and
            props['split_right_shift']):
            return "LAYOUT_60_hhkb"
        
        # WKL (Winkey-less) Layout
        if (props['total_keys'] == 61 and
            props['bottom_row']['has_blockers'] and
            any(b[1] == 4 and b[0] in [1, 14] for b in props['blockers'])):
            return "LAYOUT_60_wkl"
        
        # Tsangan Layout
        if (props['total_keys'] == 61 and
            props['bottom_row']['is_tsangan']):
            return "LAYOUT_60_tsangan"
        
        # ISO Layouts
        if props['split_left_shift']:
            if props['split_backspace']:
                return "LAYOUT_60_iso_split_bs"
            return "LAYOUT_60_iso"
        
        # ANSI Variants
        if not props['split_left_shift']:
            if props['split_backspace'] and props['split_right_shift']:
                return "LAYOUT_60_ansi_split_bs_rshift"
            if props['split_backspace']:
                return "LAYOUT_60_ansi_split_bs"
            if props['split_right_shift']:
                return "LAYOUT_60_ansi_split_rshift"
            if props['total_keys'] == 61:
                return "LAYOUT_60_ansi"
        
        # Default to basic LAYOUT if no specific layout is detected
        return "LAYOUT"

class ViaToQmkConverter:
    """Converts VIA JSON layouts to QMK JSON format."""
    
    @staticmethod
    def get_default_layer(num_keys: int) -> List[str]:
        """Generate a default layer with transparent keycodes."""
        return ["KC_TRNS"] * num_keys

    @staticmethod
    def convert(via_json: Dict) -> Dict:
        """
        Convert VIA JSON to QMK JSON format.
        Returns a dictionary in QMK JSON format.
        """
        keyboard_name = via_json.get("name", "unknown").lower().replace(" ", "_")
        layout_data = via_json["layouts"]["keymap"]
        matrix_positions = LayoutAnalyzer.get_matrix_positions(layout_data)
        num_keys = len(matrix_positions)
        layout_type = LayoutAnalyzer.detect_layout_type(layout_data)
        
        return {
            "version": 1,
            "notes": "Generated by VIA to QMK converter",
            "documentation": "This file is a QMK Configurator export. You can import this at <https://config.qmk.fm>.",
            "keyboard": keyboard_name,
            "keymap": f"{keyboard_name}_default",
            "layout": layout_type,
            "layers": [
                ViaToQmkConverter.get_default_layer(num_keys)
            ],
            "author": ""
        }

def main():
    """Main function to handle command-line operation."""
    parser = argparse.ArgumentParser(
        description='Convert VIA JSON to QMK JSON format with enhanced 60% layout detection'
    )
    parser.add_argument('input_file', help='Input VIA JSON file')
    parser.add_argument('output_file', help='Output QMK JSON file')
    parser.add_argument('--default-layer', help='Optional file containing default layer keycodes')
    parser.add_argument('--layout', help='Override auto-detected layout')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print detailed layout analysis')
    
    args = parser.parse_args()
    
    try:
        # Read VIA JSON
        with open(args.input_file, 'r') as f:
            via_json = json.load(f)
        
        # Convert to QMK format
        qmk_json = ViaToQmkConverter.convert(via_json)
        
        # Override layout if specified
        if args.layout:
            qmk_json['layout'] = args.layout
        
        # Load default layer if provided
        if args.default_layer:
            with open(args.default_layer, 'r') as f:
                default_layer = json.load(f)
                qmk_json['layers'][0] = default_layer
        
        # Write QMK JSON
        with open(args.output_file, 'w') as f:
            json.dump(qmk_json, f, indent=2)
        
        print(f"Successfully converted {args.input_file} to {args.output_file}")
        print(f"Detected layout: {qmk_json['layout']}")
        
        if args.verbose:
            props = LayoutAnalyzer.analyze_layout_properties(via_json["layouts"]["keymap"])
            print("\nLayout Analysis:")
            print(f"Total keys: {props['total_keys']}")
            print(f"Split backspace: {props['split_backspace']}")
            print(f"Split right shift: {props['split_right_shift']}")
            print(f"Split left shift: {props['split_left_shift']}")
            print(f"Standard backspace: {props['has_standard_backspace']}")
            print(f"ANSI enter: {props['has_ansi_enter']}")
            print("\nBottom Row Configuration:")
            print(f"Left modifiers width: {props['bottom_row']['left_mods']}")
            print(f"Spacebar width: {props['bottom_row']['space']}")
            print(f"Right modifiers width: {props['bottom_row']['right_mods']}")
            print(f"Standard WK: {props['bottom_row']['is_standard_wk']}")
            print(f"Tsangan: {props['bottom_row']['is_tsangan']}")
            print(f"HHKB: {props['bottom_row']['is_hhkb']}")
            
    except FileNotFoundError:
        print(f"Error: Could not find input file {args.input_file}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in input file {args.input_file}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
