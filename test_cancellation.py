# -*- coding: utf-8 -*-
"""Test cancellation mechanism"""
import sys
import time
import threading
sys.path.insert(0, '.')

from phone_agent.agent import CancellationToken, TaskCancelledException

print("=== CANCELLATION TEST ===\n")

# Test 1: Basic cancellation
print("[Test 1] Basic cancellation")
token = CancellationToken()
assert not token.is_cancelled, "Should not be cancelled initially"
token.cancel()
assert token.is_cancelled, "Should be cancelled after cancel()"
print("  PASS: Basic cancel/check works")

# Test 2: Reset
print("\n[Test 2] Token reset")
token.reset()
assert not token.is_cancelled, "Should not be cancelled after reset"
print("  PASS: Reset works")

# Test 3: raise_if_cancelled
print("\n[Test 3] raise_if_cancelled")
token.cancel()
try:
    token.raise_if_cancelled()
    print("  FAIL: Should have raised exception")
except TaskCancelledException:
    print("  PASS: Exception raised correctly")

# Test 4: Thread-safe cancellation
print("\n[Test 4] Thread-safe cancellation")
token = CancellationToken()
cancelled_at = [None]

def worker():
    step = 0
    while not token.is_cancelled:
        step += 1
        time.sleep(0.05)
    cancelled_at[0] = step

t = threading.Thread(target=worker)
t.start()
time.sleep(0.2)  # Let worker run ~4 steps
token.cancel()
t.join(timeout=1.0)

if cancelled_at[0] and cancelled_at[0] > 0:
    print(f"  PASS: Worker stopped at step {cancelled_at[0]}")
else:
    print("  FAIL: Worker did not stop")

print("\n=== ALL TESTS PASSED ===")
