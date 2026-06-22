import os
import google.agents.cli as cli
import inspect

cli_path = os.path.dirname(inspect.getfile(cli))
print("cli_path:", cli_path)

eval_path = os.path.join(cli_path, "eval")
if os.path.exists(eval_path):
    print("eval_path files:")
    for root, dirs, files in os.walk(eval_path):
        for file in files:
            print("  ", os.path.join(root, file))
else:
    print("eval_path does not exist:", eval_path)
