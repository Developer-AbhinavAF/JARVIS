#!/usr/bin/env python3
"""JARVIS Text Mode Test Script

Run this to test all text mode features interactively.
"""

import subprocess
import sys
import time

# Test commands organized by category
test_commands = {
    "Basic Communication": [
        "hello",
        "how are you",
        "what can you do",
    ],
    "System Control": [
        "system status",
        "list apps",
        "open calculator",
        "take a screenshot",
    ],
    "Web & Search": [
        "search web for python tutorials",
        "what is machine learning",
    ],
    "YouTube": [
        "play music lo-fi beats",
        "play song believer",
    ],
    "Memory": [
        "remember my name is John",
        "add todo Buy groceries",
        "what are my todos",
    ],
    "Utilities": [
        "tell me a joke",
        "flip a coin",
        "what time is it",
        "set timer 5 seconds",
    ],
    "Status": [
        "daily briefing",
        "system status",
    ],
    "Multi-Task": [
        "open calculator and notepad",
    ],
}


def print_header():
    """Print test header."""
    print("=" * 60)
    print("  JARVIS TEXT MODE - COMPLETE TEST SUITE")
    print("=" * 60)
    print()
    print("This script shows you all commands to test.")
    print("Run: python -m jarvis.main")
    print("Press 'n' for TEXT MODE")
    print()


def print_test_menu():
    """Print interactive test menu."""
    print("=" * 60)
    print("  TEST CATEGORIES")
    print("=" * 60)
    print()
    
    categories = list(test_commands.keys())
    for i, category in enumerate(categories, 1):
        print(f"{i}. {category}")
    
    print()
    print("99. Run ALL tests")
    print("0. Exit")
    print()


def print_commands(category: str) -> None:
    """Print commands for a category."""
    print()
    print("=" * 60)
    print(f"  {category.upper()}")
    print("=" * 60)
    print()
    
    commands = test_commands[category]
    for i, cmd in enumerate(commands, 1):
        print(f"  {i}. {cmd}")
    
    print()
    print("Copy these commands and paste them into JARVIS text mode")
    print()
    input("Press Enter to continue...")


def run_all_tests() -> None:
    """Print all tests."""
    print()
    print("=" * 60)
    print("  COMPLETE TEST SEQUENCE")
    print("=" * 60)
    print()
    
    all_commands = []
    for category, commands in test_commands.items():
        print(f"\n## {category}")
        for cmd in commands:
            print(f"  {cmd}")
            all_commands.append(cmd)
    
    print()
    print("=" * 60)
    print("  QUICK TEST SCRIPT (Copy all at once)")
    print("=" * 60)
    print()
    print("Run these commands in order:")
    print()
    for cmd in all_commands:
        print(cmd)
    print("exit")
    
    print()
    input("Press Enter to continue...")


def main():
    """Main test interface."""
    print_header()
    
    while True:
        print_test_menu()
        
        try:
            choice = input("Select test category (0-99): ").strip()
            
            if choice == "0":
                print("\nExiting...")
                break
            
            elif choice == "99":
                run_all_tests()
            
            elif choice.isdigit():
                idx = int(choice) - 1
                categories = list(test_commands.keys())
                
                if 0 <= idx < len(categories):
                    print_commands(categories[idx])
                else:
                    print("Invalid choice!")
            
            else:
                print("Invalid input!")
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print()
    print("=" * 60)
    print("To start testing:")
    print("  1. Run: python -m jarvis.main")
    print("  2. Press 'n' for TEXT MODE")
    print("  3. Type the test commands")
    print("=" * 60)


if __name__ == "__main__":
    main()
