![gofannon logo](https://github.com/The-AI-Alliance/gofannon/blob/main/gofannon.jpg)  
  
# gofannon  
  
**gofannon** is a collection of tools designed to enhance the capabilities of function-calling-enabled language models. These tools provide additional functionality for various tasks, including mathematical operations, GitHub interactions, arXiv searches, and advanced reasoning techniques.  

## Why the name `gofanon` ?

See [`why_the_name_gofannon.md`](./why_the_name_gofannon.md) for the rich story on why we chose to honor this Celtic Diety

## Our Mission

We aim to achieve:

### Cross-Framework Compatibility
We solve the "vendor lock-in" problem in AI tooling through:
- Standardized interface definitions
- Automatic schema translation
- Bidirectional conversion tools

### Open Source Education
We make AI development accessible by:
- Curated contribution pathways
- Interactive documentation
- Pair programming sessions
- Weekly office hours

### Encouraging First-Time Contributors
We actively support new contributors through:
- Beginner-friendly issues
- Clear documentation and guides
- Supportuve community engagement

## Features  
  
- **Basic Math Operations**: Perform addition, subtraction, multiplication, division, and exponentiation.  
- **GitHub Integration**: Interact with GitHub repositories, including creating issues, committing files, and retrieving repository contents.  
- **arXiv Search**: Search for and retrieve articles from arXiv.  
- **Advanced Reasoning**: Utilize Chain-of-Thought (CoT) and Tree-of-Thought (ToT) reasoning techniques for complex problem-solving.  
- **NHTSA Complaints**: Retrieve vehicle complaint data from the National Highway Traffic Safety Administration (NHTSA).  
  
## Roadmap  
  
For a detailed overview of planned features and their current status, please refer to the [ROADMAP](./ROADMAP.md).   

## Documentation

Documentation can be found [here](./docs).Each tool comes with its own documentation, which can be found in the docs/ directory. The documentation provides detailed information on how to use each tool, including required parameters and example usage.

## Installation  
  
To install gofannon, simply clone the repository and install the required dependencies:  
  
```bash  
git clone https://github.com/The-AI-Alliance/gofannon.git  
cd gofannon  
pip install -r requirements.txt
```

or 

```
pip install git+https://github.com/The-AI-Alliance/gofannon.git
```

## Communication Channels
- **Disccord**: Real-time collaboration and support
- **Github Discussions**: Technical deep dives and asynchhronous collaboration
- **Community Calls**: Bi-weekly video meetings

## Usage Example
```bash
import gofannon
agent = gofannon.Agent()
agent.run()
```

## License  
  
This project is licensed under the ASFv2 License. See the [LICENSE](./LICENSE) file for more details.

## Contributing  
  
We welcome contributions from the community! If you'd like to add a new tool or improve an existing one, please check out our [CONTRIBUTING](./CONTRIBUTING.md) guide for detailed instructions on how to get started.  
  
## Support  
  
If you encounter any issues or have questions, please open an issue on our [GitHub repository](https://github.com/your-repo/gofannon/issues).  
  
## Acknowledgments  
  
We would like to thank the open-source community for their contributions and support in making this project possible.  
