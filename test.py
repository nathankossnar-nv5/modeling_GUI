# extract_args_ast.py
import ast
import inspect


def extract_argparse_from_ast(script_path):
    """Extract argparse arguments by parsing the AST"""

    with open(script_path, 'r') as f:
        tree = ast.parse(f.read())

    args_info = {}

    # Find all add_argument calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if it's a call to add_argument
            if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'add_argument'):

                # Extract argument name
                if node.args:
                    arg_name = ast.literal_eval(node.args[0])
                    arg_name = arg_name.lstrip('-').replace('-', '_')

                    # Extract keyword arguments
                    arg_info = {}
                    for keyword in node.keywords:
                        try:
                            arg_info[keyword.arg] = ast.literal_eval(keyword.value)
                        except:
                            # Handle complex expressions
                            arg_info[keyword.arg] = ast.unparse(keyword.value)

                    args_info[arg_name] = arg_info

    return args_info


# Usage
config = extract_argparse_from_ast("//hio-isi02-data.prodna.quantumspatial.com/analytics/Tools/GUIs/Land_Cover_Script_Interface/scripts/compare_paths.py")
print(config)

# Output:
# {
#     'learning_rate': {'type': <class 'float'>, 'default': 0.001, 'help': 'Learning rate'},
#     'batch_size': {'type': <class 'int'>, 'default': 32, 'help': 'Batch size'},
#     ...
# }