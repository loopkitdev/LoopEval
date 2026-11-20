"""Echo controller: returns Loop's own automatic decision. Identity check for --candidate-external-controller —
a run with it must reproduce the stock candidate run exactly."""
import json, sys
for line in sys.stdin:
    m = json.loads(line)
    sys.stdout.write(json.dumps({"bolus": m["loop"]["bolus"], "temp_rate": m["loop"]["temp_rate"]}) + "\n"); sys.stdout.flush()
