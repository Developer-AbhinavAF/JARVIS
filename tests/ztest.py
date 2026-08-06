import time
import requests
import json

def test_ollama_speed(model_name="qwen2.5:3b", prompt=None):
    """
    Test the speed of an Ollama model running locally.
    
    Args:
        model_name: Name of the Ollama model to test
        prompt: Custom prompt to use (optional)
    """
    
    # Default test prompt (mix of Hinglish + coding + reasoning)
    if prompt is None:
        prompt = """Write a Python function to calculate fibonacci numbers and explain it in Hinglish. Also, what is 17 * 24?"""
    
    # Ngrok warning bypass karne ke liye header zaroori hai
    headers = {
        "ngrok-skip-browser-warning": "true"
    }

    ollama_url = os.getenv("OLLAMA_BASE_URL", "https://kiersten-nonpunishable-carry.ngrok-free.dev") + "/api/generate"
    
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,  # Get complete response at once for timing
        "options": {
            "temperature": 0.7,
            "num_predict": 200  # Limit response length for consistent testing
        }
    }
    
    print(f"🧪 Testing model: {model_name}")
    print(f"📝 Prompt: {prompt[:80]}...")
    print("-" * 60)
    
    # Start timer
    start_time = time.time()
    
    try:
        # Send request to Ollama
        response = requests.post(ollama_url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        # End timer
        end_time = time.time()
        
        # Extract metrics
        total_time = end_time - start_time
        generated_text = result.get("response", "")
        token_count = result.get("eval_count", 0)
        
        # Calculate speed
        tokens_per_second = token_count / total_time if total_time > 0 else 0
        
        print("\n✅ RESULTS:")
        print("=" * 60)
        print(f"⏱️  Total Time:        {total_time:.2f} seconds")
        print(f"🔢 Tokens Generated:   {token_count}")
        print(f"⚡ Speed:              {tokens_per_second:.2f} tokens/sec")
        print(f"📊 Avg per token:      {(total_time/token_count*1000):.1f} ms/token")
        print("=" * 60)
        
        print("\n📄 Generated Response (first 300 chars):")
        print("-" * 60)
        print(generated_text[:300] + "..." if len(generated_text) > 300 else generated_text)
        print("-" * 60)
        
        # Performance rating
        print("\n🎯 PERFORMANCE RATING:")
        if tokens_per_second >= 20:
            print("⭐⭐⭐⭐⭐ EXCELLENT! Very fast on your hardware")
        elif tokens_per_second >= 10:
            print("⭐⭐⭐⭐ GOOD! Decent speed for your specs")
        elif tokens_per_second >= 5:
            print("⭐⭐⭐ OKAY! Usable but could be faster")
        elif tokens_per_second >= 2:
            print("⭐⭐ SLOW! Consider smaller model or quantization")
        else:
            print("⭐ VERY SLOW! Upgrade hardware or use smaller model")
        
        return {
            "model": model_name,
            "total_time": round(total_time, 2),
            "tokens_generated": token_count,
            "tokens_per_second": round(tokens_per_second, 2),
            "ms_per_token": round((total_time/token_count*1000), 1) if token_count > 0 else 0
        }
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to Ollama!")
        print("💡 Make sure Ollama is running: 'ollama serve'")
        return None
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None


def compare_models(models=["qwen3:1.7b-q4_k_m", "qwen2.5:3b"]):
    """Compare speed across multiple models."""
    
    print("\n" + "=" * 70)
    print("🔄 COMPARATIVE BENCHMARK ACROSS MODELS")
    print("=" * 70)
    
    results = []
    
    for model in models:
        print(f"\n{'=' * 70}")
        result = test_ollama_speed(model)
        if result:
            results.append(result)
        time.sleep(2)  # Small pause between tests
    
    # Summary table
    if results:
        print("\n\n" + "=" * 70)
        print("📊 SUMMARY TABLE")
        print("=" * 70)
        print(f"{'Model':<25} {'Speed (tok/s)':<15} {'Time (s)':<12} {'Tokens':<10}")
        print("-" * 70)
        
        # Sort by speed (fastest first)
        results.sort(key=lambda x: x["tokens_per_second"], reverse=True)
        
        for r in results:
            print(f"{r['model']:<25} {r['tokens_per_second']:<15.2f} {r['total_time']:<12.2f} {r['tokens_generated']:<10}")
        
        print("=" * 70)
        print(f"\n🏆 FASTEST MODEL: {results[0]['model']} ({results[0]['tokens_per_second']} tok/s)")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # If model name provided as argument
        model_to_test = sys.argv[1]
        test_ollama_speed(model_to_test)
    else:
        # Default: test single model
        print("Choose option:")
        print("1. Test single model (default: qwen2.5-coder:3b)")
        print("2. Compare multiple models")
        
        choice = input("\nEnter choice (1/2): ").strip()
        
        if choice == "2":
            compare_models()
        else:
            model = input("Enter model name (or press Enter for default): ").strip()
            if not model:
                model = "qwen2.5-coder:3b"
            test_ollama_speed(model)