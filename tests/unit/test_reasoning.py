import pytest
from os import getenv
from gofannon.reasoning.hierarchical_cot import HierarchicalCoT
from gofannon.reasoning.sequential_cot import SequentialCoT
from gofannon.reasoning.tree_of_thought import TreeOfThought
depth_chart = [
    {'model_name' : "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
     'base_url' : "https://api.deepinfra.com/v1/openai",
     'api_key' : getenv("DEEPINFRA_TOKEN"),
     'temperature' : 0.3,
     'prompt_appendix' : 'This isnt used at level 0.'
     },
    {'model_name' : "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
     'base_url' : "https://api.deepinfra.com/v1/openai",
     'api_key' : getenv("DEEPINFRA_TOKEN"),
     'temperature' : 0.3,
     },
    {'model_name' : "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
     'base_url' : "https://api.deepinfra.com/v1/openai",
     'api_key' : getenv("DEEPINFRA_TOKEN"),
     'temperature' : 0.3,
     }
]

def test_hierarchical_cot():
    hierarchical_cot = HierarchicalCoT(depth_chart= depth_chart)
    result = hierarchical_cot.fn("Explain quantum computing", depth=3)
    assert result is not None

# def test_sequential_cot():
#     sequential_cot = SequentialCoT(depth_chart= depth_chart)
#     result = sequential_cot.fn("Explain quantum computing", steps=3)
#     assert result is not None

def test_tree_of_thought():
    tree_of_thought = TreeOfThought(depth_chart= depth_chart)
    result = tree_of_thought.fn("Explain quantum computing", branches=3)
    assert result is not None