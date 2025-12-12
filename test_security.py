import sys
sys.path.insert(0, '.')
from phone_agent.actions.handler import parse_action

# Test 1: Normal Tap
r1 = parse_action('do(action="Tap", element=[500, 500])')
t1 = r1.get('action') == 'Tap' and r1.get('_metadata') == 'do'
print(f"Test1 Tap: {'PASS' if t1 else 'FAIL'}")

# Test 2: Finish
r2 = parse_action('finish(message="done")')
t2 = r2.get('_metadata') == 'finish' and r2.get('message') == 'done'
print(f"Test2 Finish: {'PASS' if t2 else 'FAIL'}")

# Test 3: Malicious - should raise ValueError
t3 = False
try:
    parse_action('do(action="Tap", element=[__import__("os"), 500])')
except ValueError:
    t3 = True
print(f"Test3 Block __import__: {'PASS' if t3 else 'FAIL'}")

# Test 4: Malicious - variable reference
t4 = False
try:
    parse_action('do(action="Tap", element=[x, 500])')
except ValueError:
    t4 = True
print(f"Test4 Block variable: {'PASS' if t4 else 'FAIL'}")

# Test 5: Malicious - function call
t5 = False
try:
    parse_action('do(action="Tap", element=[print("hacked"), 500])')
except ValueError:
    t5 = True
print(f"Test5 Block function: {'PASS' if t5 else 'FAIL'}")

all_pass = t1 and t2 and t3 and t4 and t5
print(f"\nALL TESTS: {'PASS' if all_pass else 'FAIL'}")
