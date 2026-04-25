"""jarvis.academic_tools

Advanced academic tools for mathematics, physics, and coordinate geometry.
Expert-level computations with graph plotting capabilities.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
from typing import Any, Dict, List, Tuple

import numpy as np

from jarvis import config

logger = logging.getLogger(__name__)


def solve_math(expression: str, show_steps: bool = True) -> str:
    """Solve mathematical expressions with step-by-step working.
    
    Args:
        expression: Mathematical expression to solve (e.g., "2x + 5 = 15", "integrate x^2")
        show_steps: Whether to show step-by-step solution
    """
    try:
        import sympy as sp
        from sympy import symbols, Eq, solve, simplify, integrate, diff, limit, series, expand, factor
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
        
        expr = expression.strip()
        
        # Check for equation solving
        if '=' in expr and not expr.startswith('y='):
            # Extract left and right sides
            parts = expr.split('=')
            if len(parts) == 2:
                left, right = parts[0].strip(), parts[1].strip()
                
                # Determine variables
                var_match = re.findall(r'[a-zA-Z]', expr)
                if var_match:
                    var = symbols(var_match[0])
                    try:
                        left_expr = parse_expr(left, transformations=standard_transformations + (implicit_multiplication_application,), local_dict={var_match[0]: var})
                        right_expr = parse_expr(right, transformations=standard_transformations + (implicit_multiplication_application,), local_dict={var_match[0]: var})
                        eq = Eq(left_expr, right_expr)
                        solutions = solve(eq, var)
                        
                        if show_steps:
                            steps = f"📐 **Solving: {expression}**\n\n"
                            steps += f"Step 1: Rearrange equation\n"
                            steps += f"   {left} = {right}\n"
                            steps += f"Step 2: Bring all terms to one side\n"
                            steps += f"   {left_expr - right_expr} = 0\n"
                            steps += f"Step 3: Solve for {var}\n"
                            if solutions:
                                steps += f"   {var} = {solutions}\n\n"
                                steps += f"✅ **Answer: {var} = {solutions}**"
                            else:
                                steps += f"   No solution found"
                            return steps
                        else:
                            return f"Solution: {var} = {solutions}"
                    except Exception as e:
                        return f"Could not solve equation: {e}"
        
        # Check for integration
        if any(word in expr.lower() for word in ['integrate', 'integration', '∫']):
            expr_clean = expr.lower().replace('integrate', '').replace('integration', '').replace('∫', '').replace('dx', '').strip()
            x = symbols('x')
            try:
                parsed = parse_expr(expr_clean, transformations=standard_transformations + (implicit_multiplication_application,), local_dict={'x': x})
                result = integrate(parsed, x)
                if show_steps:
                    return f"📐 **Integration**\n\n∫ ({expr_clean}) dx\n\nStep 1: Apply integration rules\nStep 2: Find antiderivative\n\n✅ **Result: {result} + C**"
                return f"∫ {expr_clean} dx = {result} + C"
            except Exception as e:
                return f"Could not integrate: {e}"
        
        # Check for differentiation
        if any(word in expr.lower() for word in ['differentiate', 'derivative', "d/d"]):
            expr_clean = re.sub(r'differentiate|derivative|d/dx', '', expr, flags=re.IGNORECASE).strip()
            x = symbols('x')
            try:
                parsed = parse_expr(expr_clean, transformations=standard_transformations + (implicit_multiplication_application,), local_dict={'x': x})
                result = diff(parsed, x)
                if show_steps:
                    return f"📐 **Differentiation**\n\nd/dx ({expr_clean})\n\nStep 1: Apply differentiation rules\nStep 2: Compute derivative\n\n✅ **Result: {result}**"
                return f"d/dx ({expr_clean}) = {result}"
            except Exception as e:
                return f"Could not differentiate: {e}"
        
        # Simple evaluation
        try:
            transformations = standard_transformations + (implicit_multiplication_application,)
            parsed = parse_expr(expr, transformations=transformations)
            result = float(parsed.evalf())
            return f"📊 **Result: {result}**"
        except:
            # Try direct Python eval for simple cases
            try:
                # Safe evaluation
                allowed = {'math': math, 'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos, 
                          'tan': math.tan, 'log': math.log, 'exp': math.exp, 'pi': math.pi,
                          'e': math.e, 'pow': pow, 'abs': abs}
                result = eval(expr, {"__builtins__": {}}, allowed)
                return f"📊 **Result: {result}**"
            except Exception as e:
                return f"Could not evaluate: {e}"
                
    except ImportError:
        return "Math solving requires sympy. Run: pip install sympy"
    except Exception as e:
        return f"Math error: {e}"


def plot_advanced_graph(
    graph_type: str,
    data: Dict[str, Any],
    title: str = "Graph",
    xlabel: str = "X",
    ylabel: str = "Y",
    save_path: str = None
) -> str:
    """Plot advanced graphs with matplotlib and save to file.
    
    Args:
        graph_type: Type of graph - line, bar, pie, scatter, histogram, area, 
                   polar, 3d_line, 3d_scatter, coordinate_geometry
        data: Graph data - varies by type
        title: Graph title
        xlabel: X-axis label
        ylabel: Y-axis label
        save_path: Optional path to save graph image (auto-generated if not provided)
        
    Returns:
        Path to saved graph image file
    """
    
    from datetime import datetime
    
    # Auto-generate save path in JARVIS root if not provided
    if not save_path:
        graphs_dir = os.path.join(config.JARVIS_ROOT, "graphs")
        os.makedirs(graphs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(graphs_dir, f"graph_{graph_type}_{timestamp}.png")
    
    def _plot_worker():
        try:
            import matplotlib
            # Use non-interactive Agg backend (no GUI needed)
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D
            
            plt.style.use("dark_background")
            
            graph_type_lower = graph_type.lower()
            
            # Coordinate Geometry - Plot points, lines, shapes
            if graph_type_lower == "coordinate_geometry":
                fig, ax = plt.subplots(figsize=(10, 10))
                ax.set_aspect('equal')
                
                # Extract data
                points = data.get('points', [])  # [(x1,y1), (x2,y2), ...]
                lines = data.get('lines', [])  # [((x1,y1), (x2,y2)), ...]
                shapes = data.get('shapes', [])  # ['circle', 'rectangle', etc.]
                
                # Plot points
                if points:
                    xs, ys = zip(*points)
                    ax.scatter(xs, ys, c='cyan', s=100, zorder=5)
                    for i, (x, y) in enumerate(points):
                        ax.annotate(f'P{i+1}({x},{y})', (x, y), xytext=(5, 5), 
                                   textcoords='offset points', color='white', fontsize=9)
                
                # Plot lines
                for line in lines:
                    (x1, y1), (x2, y2) = line
                    ax.plot([x1, x2], [y1, y2], 'g-', linewidth=2)
                    # Show line equation
                    if x2 != x1:
                        slope = (y2 - y1) / (x2 - x1)
                        ax.annotate(f'slope={slope:.2f}', ((x1+x2)/2, (y1+y2)/2), 
                                   color='yellow', fontsize=8)
                
                # Draw shapes
                for shape in shapes:
                    if shape['type'] == 'circle':
                        center = shape.get('center', (0, 0))
                        radius = shape.get('radius', 1)
                        circle = plt.Circle(center, radius, fill=False, color='red', linewidth=2)
                        ax.add_patch(circle)
                        ax.annotate(f'r={radius}', (center[0], center[1]+radius), 
                                   color='red', fontsize=9)
                    elif shape['type'] == 'rectangle':
                        corners = shape.get('corners', [(0,0), (1,0), (1,1), (0,1)])
                        rect = plt.Polygon(corners, fill=False, color='orange', linewidth=2)
                        ax.add_patch(rect)
                
                ax.axhline(y=0, color='w', linestyle='-', alpha=0.3)
                ax.axvline(x=0, color='w', linestyle='-', alpha=0.3)
                ax.grid(True, alpha=0.3)
                ax.set_xlabel('X-axis')
                ax.set_ylabel('Y-axis')
                ax.set_title(title or 'Coordinate Geometry')
                
            # 3D plots
            elif graph_type_lower in ['3d_line', '3d_scatter', '3d_surface']:
                fig = plt.figure(figsize=(10, 8))
                ax = fig.add_subplot(111, projection='3d')
                
                if 'x' in data and 'y' in data and 'z' in data:
                    x, y, z = data['x'], data['y'], data['z']
                    
                    if graph_type_lower == '3d_scatter':
                        ax.scatter(x, y, z, c=z, cmap='cool', s=50)
                    elif graph_type_lower == '3d_line':
                        ax.plot(x, y, z, linewidth=2, color='cyan')
                    elif graph_type_lower == '3d_surface' and 'X' in data and 'Y' in data and 'Z' in data:
                        ax.plot_surface(data['X'], data['Y'], data['Z'], cmap='cool')
                    
                    ax.set_xlabel(xlabel)
                    ax.set_ylabel(ylabel)
                    ax.set_zlabel('Z')
                
            # Polar plot
            elif graph_type_lower == 'polar':
                fig = plt.figure(figsize=(8, 8))
                ax = fig.add_subplot(111, projection='polar')
                
                theta = data.get('theta', [])
                r = data.get('r', [])
                
                if theta and r:
                    ax.plot(theta, r, 'cyan', linewidth=2)
                    ax.fill(theta, r, alpha=0.3, color='cyan')
                    ax.set_title(title, pad=20)
                
            # Area chart
            elif graph_type_lower == 'area':
                fig, ax = plt.subplots(figsize=(10, 6))
                x = data.get('x', [])
                y = data.get('y', [])
                
                if x and y:
                    ax.fill_between(x, y, alpha=0.5, color='cyan')
                    ax.plot(x, y, 'w-', linewidth=2)
                    ax.set_xlabel(xlabel)
                    ax.set_ylabel(ylabel)
                    ax.set_title(title)
                    ax.grid(True, alpha=0.3)
                
            # Histogram
            elif graph_type_lower == 'histogram':
                fig, ax = plt.subplots(figsize=(10, 6))
                values = data.get('values', [])
                bins = data.get('bins', 10)
                
                if values:
                    n, bins_out, patches = ax.hist(values, bins=bins, color='cyan', alpha=0.7, edgecolor='white')
                    ax.set_xlabel(xlabel)
                    ax.set_ylabel('Frequency')
                    ax.set_title(title)
                    ax.grid(True, alpha=0.3, axis='y')
                    
                    # Add statistics
                    mean_val = np.mean(values)
                    std_val = np.std(values)
                    ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f}')
                    ax.legend()
                
            # Scatter plot
            elif graph_type_lower == 'scatter':
                fig, ax = plt.subplots(figsize=(10, 6))
                x = data.get('x', [])
                y = data.get('y', [])
                
                if x and y:
                    colors = data.get('colors', None)
                    sizes = data.get('sizes', None)
                    ax.scatter(x, y, c=colors, s=sizes, alpha=0.6, cmap='cool')
                    ax.set_xlabel(xlabel)
                    ax.set_ylabel(ylabel)
                    ax.set_title(title)
                    ax.grid(True, alpha=0.3)
                
            # Standard line/bar/pie
            else:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                labels = data.get('labels', [])
                values = data.get('values', [])
                
                if graph_type_lower == 'pie':
                    colors = plt.cm.cool(np.linspace(0, 1, len(values)))
                    ax.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                    ax.set_title(title)
                elif graph_type_lower == 'bar':
                    x_pos = range(len(labels))
                    colors = plt.cm.cool(np.linspace(0, 1, len(values)))
                    ax.bar(x_pos, values, color=colors, edgecolor='white')
                    ax.set_xticks(x_pos)
                    ax.set_xticklabels(labels, rotation=45, ha='right')
                    ax.set_ylabel(ylabel)
                    ax.set_title(title)
                    ax.grid(True, alpha=0.3, axis='y')
                else:  # line
                    ax.plot(labels, values, marker='o', linewidth=2, color='cyan', markersize=8)
                    ax.set_xlabel(xlabel)
                    ax.set_ylabel(ylabel)
                    ax.set_title(title)
                    ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Always save to file (no GUI display in backend)
            plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='black')
            logger.info(f"✅ Graph saved to: {save_path}")
            plt.close(fig)  # Clean up memory
            
        except Exception as e:
            logger.exception("Advanced graph plotting failed")
            print(f"Graph error: {e}")
    
    # Run synchronously to ensure file is created before returning
    _plot_worker()
    
    # Return the file path for frontend to display
    return f"📊 {graph_type.title()} graph created! Image saved at: {save_path}"


def solve_physics(problem: str, topic: str = None) -> str:
    """Solve physics problems with formulas and explanations.
    
    Args:
        problem: Physics problem description
        topic: Optional topic (mechanics, electromagnetism, thermodynamics, etc.)
    """
    try:
        import sympy as sp
        
        problem_lower = problem.lower()
        
        # Mechanics
        if topic == "mechanics" or any(word in problem_lower for word in ['force', 'mass', 'acceleration', 'velocity', 'momentum', 'energy', 'work']):
            
            # Newton's Second Law: F = ma
            if any(phrase in problem_lower for phrase in ['f = ma', 'force = mass * acceleration', 'calculate force']):
                # Try to extract values
                mass_match = re.search(r'(\d+\.?\d*)\s*kg', problem_lower)
                accel_match = re.search(r'(\d+\.?\d*)\s*m/s[²2]', problem_lower)
                
                if mass_match and accel_match:
                    m = float(mass_match.group(1))
                    a = float(accel_match.group(1))
                    F = m * a
                    return f"🔬 **Newton's Second Law**\n\nGiven:\n• Mass (m) = {m} kg\n• Acceleration (a) = {a} m/s²\n\nFormula: F = ma\n\nF = {m} × {a}\n\n✅ **Force (F) = {F} N (Newtons)**"
                else:
                    return "🔬 **Newton's Second Law: F = ma**\n\nWhere:\n• F = Force (Newtons)\n• m = Mass (kg)\n• a = Acceleration (m/s²)\n\nProvide mass and acceleration to calculate force."
            
            # Kinetic Energy: KE = ½mv²
            if any(phrase in problem_lower for phrase in ['kinetic energy', 'ke = ', 'energy of motion']):
                mass_match = re.search(r'(\d+\.?\d*)\s*kg', problem_lower)
                velocity_match = re.search(r'(\d+\.?\d*)\s*m/s', problem_lower)
                
                if mass_match and velocity_match:
                    m = float(mass_match.group(1))
                    v = float(velocity_match.group(1))
                    KE = 0.5 * m * v**2
                    return f"🔬 **Kinetic Energy**\n\nGiven:\n• Mass (m) = {m} kg\n• Velocity (v) = {v} m/s\n\nFormula: KE = ½mv²\n\nKE = ½ × {m} × {v}²\nKE = 0.5 × {m} × {v**2}\n\n✅ **Kinetic Energy = {KE:.2f} Joules**"
                else:
                    return "🔬 **Kinetic Energy: KE = ½mv²**\n\nWhere:\n• KE = Kinetic Energy (Joules)\n• m = Mass (kg)\n• v = Velocity (m/s)"
            
            # Potential Energy: PE = mgh
            if any(phrase in problem_lower for phrase in ['potential energy', 'pe = ', 'gravitational potential']):
                mass_match = re.search(r'(\d+\.?\d*)\s*kg', problem_lower)
                height_match = re.search(r'(\d+\.?\d*)\s*m(?:\s|$|\n)', problem_lower)
                
                g = 9.8  # m/s²
                
                if mass_match and height_match:
                    m = float(mass_match.group(1))
                    h = float(height_match.group(1))
                    PE = m * g * h
                    return f"🔬 **Gravitational Potential Energy**\n\nGiven:\n• Mass (m) = {m} kg\n• Height (h) = {h} m\n• g = 9.8 m/s²\n\nFormula: PE = mgh\n\nPE = {m} × 9.8 × {h}\n\n✅ **Potential Energy = {PE:.2f} Joules**"
                else:
                    return "🔬 **Gravitational Potential Energy: PE = mgh**\n\nWhere:\n• PE = Potential Energy (Joules)\n• m = Mass (kg)\n• g = 9.8 m/s² (acceleration due to gravity)\n• h = Height (m)"
        
        # Electromagnetism
        if topic == "electromagnetism" or any(word in problem_lower for word in ['electric', 'magnetic', 'current', 'voltage', 'resistance', 'ohm']):
            
            # Ohm's Law: V = IR
            if any(phrase in problem_lower for phrase in ['ohm', 'v = ir', 'voltage = current * resistance']):
                voltage_match = re.search(r'(\d+\.?\d*)\s*v(?:olt|olts)?', problem_lower)
                current_match = re.search(r'(\d+\.?\d*)\s*a(?:mp|mps|mpere|mperes)?', problem_lower)
                resistance_match = re.search(r'(\d+\.?\d*)\s*o(?:hm|hms|hms)?', problem_lower)
                
                # Determine what's being asked
                if 'find voltage' in problem_lower or 'calculate voltage' in problem_lower:
                    if current_match and resistance_match:
                        I = float(current_match.group(1))
                        R = float(resistance_match.group(1))
                        V = I * R
                        return f"⚡ **Ohm's Law**\n\nGiven:\n• Current (I) = {I} A\n• Resistance (R) = {R} Ω\n\nFormula: V = IR\n\nV = {I} × {R}\n\n✅ **Voltage (V) = {V:.2f} Volts**"
                
                elif 'find current' in problem_lower or 'calculate current' in problem_lower:
                    if voltage_match and resistance_match:
                        V = float(voltage_match.group(1))
                        R = float(resistance_match.group(1))
                        I = V / R
                        return f"⚡ **Ohm's Law**\n\nGiven:\n• Voltage (V) = {V} V\n• Resistance (R) = {R} Ω\n\nFormula: I = V/R\n\nI = {V} ÷ {R}\n\n✅ **Current (I) = {I:.3f} Amperes**"
                
                elif 'find resistance' in problem_lower or 'calculate resistance' in problem_lower:
                    if voltage_match and current_match:
                        V = float(voltage_match.group(1))
                        I = float(current_match.group(1))
                        R = V / I
                        return f"⚡ **Ohm's Law**\n\nGiven:\n• Voltage (V) = {V} V\n• Current (I) = {I} A\n\nFormula: R = V/I\n\nR = {V} ÷ {I}\n\n✅ **Resistance (R) = {R:.2f} Ohms**"
                
                else:
                    return "⚡ **Ohm's Law: V = IR**\n\nWhere:\n• V = Voltage (Volts)\n• I = Current (Amperes)\n• R = Resistance (Ohms)\n\nVariations:\n• I = V/R (find current)\n• R = V/I (find resistance)"
        
        # Thermodynamics
        if topic == "thermodynamics" or any(word in problem_lower for word in ['temperature', 'heat', 'thermal', 'entropy']):
            if any(phrase in problem_lower for phrase in ['celsius to fahrenheit', 'c to f']):
                c_match = re.search(r'(\d+\.?\d*)\s*[°]?\s*c', problem_lower)
                if c_match:
                    C = float(c_match.group(1))
                    F = (C * 9/5) + 32
                    return f"🌡️ **Temperature Conversion**\n\nGiven: {C}°C\n\nFormula: °F = (°C × 9/5) + 32\n\n°F = ({C} × 9/5) + 32\n°F = {C * 9/5} + 32\n\n✅ **{C}°C = {F:.1f}°F**"
            
            if any(phrase in problem_lower for phrase in ['fahrenheit to celsius', 'f to c']):
                f_match = re.search(r'(\d+\.?\d*)\s*[°]?\s*f', problem_lower)
                if f_match:
                    F = float(f_match.group(1))
                    C = (F - 32) * 5/9
                    return f"🌡️ **Temperature Conversion**\n\nGiven: {F}°F\n\nFormula: °C = (°F - 32) × 5/9\n\n°C = ({F} - 32) × 5/9\n°C = {F - 32} × 5/9\n\n✅ **{F}°F = {C:.1f}°C**"
        
        return f"🔬 **Physics Problem**\n\nProblem: {problem}\n\nI can help with:\n• **Mechanics**: Force, Energy, Motion (F=ma, KE=½mv², PE=mgh)\n• **Electromagnetism**: Ohm's Law, circuits (V=IR)\n• **Thermodynamics**: Temperature conversions, heat transfer\n\nSpecify the topic or provide values to calculate."
        
    except ImportError:
        return "Physics solving requires sympy. Run: pip install sympy"
    except Exception as e:
        return f"Physics error: {e}"


def coordinate_geometry(operation: str, **kwargs) -> str:
    """Perform coordinate geometry calculations.
    
    Args:
        operation: Type of operation - distance, midpoint, slope, line_equation, 
                  area_triangle, area_polygon, circle_equation, intersection
        **kwargs: Operation-specific parameters
    """
    try:
        import sympy as sp
        from sympy.geometry import Point, Line, Circle, Triangle, Polygon
        
        if operation == "distance":
            x1, y1 = kwargs.get('p1', (0, 0))
            x2, y2 = kwargs.get('p2', (0, 0))
            
            distance = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            
            return f"📐 **Distance Between Points**\n\nPoint A: ({x1}, {y1})\nPoint B: ({x2}, {y2})\n\nFormula: d = √[(x₂-x₁)² + (y₂-y₁)²]\n\nd = √[({x2}-{x1})² + ({y2}-{y1})²]\nd = √[{(x2-x1)**2} + {(y2-y1)**2}]\nd = √{((x2-x1)**2 + (y2-y1)**2)}\n\n✅ **Distance = {distance:.4f} units**"
        
        elif operation == "midpoint":
            x1, y1 = kwargs.get('p1', (0, 0))
            x2, y2 = kwargs.get('p2', (0, 0))
            
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            return f"📐 **Midpoint**\n\nPoint A: ({x1}, {y1})\nPoint B: ({x2}, {y2})\n\nFormula: M = ((x₁+x₂)/2, (y₁+y₂)/2)\n\nM = (({x1}+{x2})/2, ({y1}+{y2})/2)\nM = ({x1+x2}/2, {y1+y2}/2)\n\n✅ **Midpoint = ({mid_x}, {mid_y})**"
        
        elif operation == "slope":
            x1, y1 = kwargs.get('p1', (0, 0))
            x2, y2 = kwargs.get('p2', (0, 0))
            
            if x2 == x1:
                return f"📐 **Slope**\n\nPoint A: ({x1}, {y1})\nPoint B: ({x2}, {y2})\n\n⚠️ **Undefined slope** (vertical line - x values are equal)"
            
            slope = (y2 - y1) / (x2 - x1)
            
            # Determine line type
            if slope == 0:
                line_type = "Horizontal line"
            elif slope > 0:
                line_type = "Rising line (positive slope)"
            else:
                line_type = "Falling line (negative slope)"
            
            return f"📐 **Slope Calculation**\n\nPoint A: ({x1}, {y1})\nPoint B: ({x2}, {y2})\n\nFormula: m = (y₂-y₁)/(x₂-x₁)\n\nm = ({y2}-{y1})/({x2}-{x1})\nm = {y2-y1}/{x2-x1}\n\n✅ **Slope (m) = {slope:.4f}**\n\n{line_type}"
        
        elif operation == "line_equation":
            x1, y1 = kwargs.get('p1', (0, 0))
            x2, y2 = kwargs.get('p2', (0, 0))
            
            if x2 == x1:
                return f"📐 **Line Equation**\n\nPoint A: ({x1}, {y1})\nPoint B: ({x2}, {y2})\n\n✅ **Equation: x = {x1}** (Vertical line)"
            
            slope = (y2 - y1) / (x2 - x1)
            # y - y1 = m(x - x1)
            # y = mx - mx1 + y1
            intercept = y1 - slope * x1
            
            return f"📐 **Line Equation**\n\nPoint A: ({x1}, {y1})\nPoint B: ({x2}, {y2})\n\nStep 1: Find slope\nm = (y₂-y₁)/(x₂-x₁) = {slope:.4f}\n\nStep 2: Using point-slope form\ny - {y1} = {slope:.4f}(x - {x1})\n\n✅ **Slope-Intercept Form: y = {slope:.4f}x + {intercept:.4f}**"
        
        elif operation == "area_triangle":
            points = kwargs.get('points', [(0,0), (1,0), (0,1)])
            if len(points) == 3:
                (x1, y1), (x2, y2), (x3, y3) = points
                # Area = ½|x₁(y₂-y₃) + x₂(y₃-y₁) + x₃(y₁-y₂)|
                area = 0.5 * abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
                
                return f"📐 **Triangle Area**\n\nVertices:\n• A({x1}, {y1})\n• B({x2}, {y2})\n• C({x3}, {y3})\n\nFormula: Area = ½|x₁(y₂-y₃) + x₂(y₃-y₁) + x₃(y₁-y₂)|\n\nArea = ½|{x1}({y2}-{y3}) + {x2}({y3}-{y1}) + {x3}({y1}-{y2})|\nArea = ½|{x1*(y2-y3)} + {x2*(y3-y1)} + {x3*(y1-y2)}|\nArea = ½|{x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)}|\n\n✅ **Area = {area:.4f} square units**"
        
        elif operation == "circle_equation":
            h, k = kwargs.get('center', (0, 0))
            r = kwargs.get('radius', 1)
            
            return f"📐 **Circle Equation**\n\nCenter: ({h}, {k})\nRadius: {r}\n\nStandard Form: (x-h)² + (y-k)² = r²\n\n✅ **Equation: (x-{h})² + (y-{k})² = {r}² = {r**2}**\n\nOr expanded:\nx² - {2*h}x + y² - {2*k}y + {h**2 + k**2 - r**2} = 0"
        
        else:
            available = ["distance", "midpoint", "slope", "line_equation", "area_triangle", "circle_equation"]
            return f"📐 **Coordinate Geometry**\n\nAvailable operations:\n• {', '.join(available)}\n\nUsage: coordinate_geometry(operation='distance', p1=(0,0), p2=(3,4))"
            
    except ImportError:
        return "Coordinate geometry requires sympy. Run: pip install sympy"
    except Exception as e:
        return f"Geometry error: {e}"


# Registry for academic tools
ACADEMIC_REGISTRY = {
    "solve_math": solve_math,
    "solve_physics": solve_physics,
    "coordinate_geometry": coordinate_geometry,
    "plot_advanced_graph": plot_advanced_graph,
}
