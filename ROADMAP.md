# Project Gofannon  - Roadmap
  
This project contains tools that can be used in LLMs. Each tool is designed to perform specific functions and can be extended or customized based on your needs.  
  
## Tools Overview  
  
| API                | Documentation                              | Status                                |  
|--------------------|--------------------------------------------|---------------------------------------|  
| GitHub             | [Documentation](docs/github/index.md)      | :construction: Under Construction     |
| Reasoning          | [Documentation](docs/reasoning/index.md)   | :construction: Under Construction        | 
| HeadlessWebBrowser | [Documentation](docs/headless_browswer) | :construction: Under Construction | 
| NHSTA              | [ComplaintsByVehicle](docs/nhsta/index.md) | :construction: Under Construction        |
| Google Search      | [Documentation](docs/google_search/index.md) | :construction: Under Construction |
| ArXiv              | [Documentation](docs/arxiv/index.md)       | :white_check_mark: Implemented        |
| Basic Math         | [Documentation](docs/basic_math/index.md)  | :white_check_mark: Implemented        |
| City of Chicago    | 311 API                                    | :triangular_flag_on_post: Roadmap     |
| DeepInfra          | WriteCode                                  | :triangular_flag_on_post: Roadmap     |
 
## Status Icons  
  
- :white_check_mark: **Implemented**: This tool is fully implemented and ready for use.  
- :construction: **In Progress**: This tool is currently under development.  
- :triangular_flag_on_post: **Roadmap**: This tool is planned for future implementation.  
- :hourglass_flowing_sand: **Low Priority**: This tool is considered low priority and may be implemented in the future.  
- :x: **Won't Implement**: There are no plans to implement this tool.  
  
## Usage  
  
To use a tool, extend the `BaseTool` class in your implementation:  
  
```python  
from base_tool import BaseTool  
  
class CustomTool(BaseTool):  
    @property  
    def definition(self):  
        return {  
            "name": "CustomTool",  
            "description": "This is a custom tool example",  
            "version": "1.0.0"  
        }  
  
    def fn(self, *args, **kwargs):  
        # Implement your functionality here  
        pass  
```
