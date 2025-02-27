# Contributing

A minimal contribution requires the following steps:
- Add a directory under `gofannon/` if your API isn't already listed.
- Add the class which extends `gofannon/base_tool/BaseTool` in the directory.
- Make sure to fill out the definition method as well as the fn method.
- Add documentation in `docs/<your-api>/<your-fn-name>.md` for your API.
- Add the function, with a link to your docs in the `index.md` file in `docs/<your-api>/`.
- If it is a new API, add it in `ROADMAP.md`


Example usage:
```python  
from gofannon.base import BaseTool  
  
class NewTool(BaseTool):  
    def __init__(self):  
        super().__init__()  
  
    @property  
    def definition(self):  
        return {  
            # Define your tool metadata and configuration  
        }  
  
    def fn(self, *args, **kwargs):  
        # Define your tool functionality  
        pass  
```

## PR Requirements

- Code changes require:
    - Passing unit tests
    - Code review approval
    - Updated documentation if API changes (or for additions)

- Documentation changes require:
    - Successful site build
    - No code review required (but still appreciated)

- Mixed changes must satisfy all relevant requirements  