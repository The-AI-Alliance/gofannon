---  
layout: default  
title: Making Your First Contribution
---  

# Your First Open Source Contribution

Welcome to the Gofannon community! This guide will walk you through making your first contribution step by step.

## Step 1: Set Up Your Development Environment

1. **Install Python 3.10+**
    - Download from [python.org](https://www.python.org/downloads/)
    - Verify installation: `python --version`

2. **Install Git**
    - Download from [git-scm.com](https://git-scm.com/)
    - Verify installation: `git --version`

3. **Set Up GitHub Account**
    - Create account at [github.com](https://github.com/)
    - Set up SSH keys: [GitHub Guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

## Step 2: Fork and Clone the Repository

1. **Fork the Repository**
    - Go to [Gofannon GitHub](https://github.com/The-AI-Alliance/gofannon)
    - Click "Fork" in the top right

2. **Clone Your Fork**  
   ```bash  
   git clone git@github.com:YOUR_USERNAME/gofannon.git  
   cd gofannon  
   ```

3. **Set Up Remote**  
   ```bash  
   git remote add upstream git@github.com:The-AI-Alliance/gofannon.git  
   ```

## Step 3: Set Up the Project

1. **Install Dependencies**  
   ```bash  
   pip install poetry  
   poetry install --all-extras  
   ```

2. **Run Tests**  
   ```bash  
   poetry run pytest  
   ```

## Step 4: Find an Issue to Work On

1. **Browse Issues**
    - Go to [Issues](https://github.com/The-AI-Alliance/gofannon/issues)
    - Look for "good first issue" labels
    - You can also propose a new function (there is a template for doing this).

2. **Claim the Issue**
    - Comment on the issue saying you'd like to work on it
    - Wait for maintainer approval

## Step 5: Make Your Changes

1. **Create a New Branch**  
   ```bash  
   git checkout -b feature/your-feature-name  
   ```

2. **Make Your Changes**
    - Follow the [contribution guidelines](https://github.com/The-AI-Alliance/gofannon/blob/main/CONTRIBUTING.md)
    - Write tests for your changes
    - Update documentation if needed

3. **Commit Your Changes**  
   ```bash  
   git add .  
   git commit -s -m "Your commit message"  
   ```

## Step 6: Push and Create a Pull Request

1. **Push Your Branch**  
   ```bash  
   git push origin feature/your-feature-name  
   ```

2. **Create Pull Request**
    - Go to your fork on GitHub
    - Click "Compare & pull request"
    - Fill out the PR template
    - Link to the issue you're addressing

## Step 7: Address Feedback

1. **Respond to Reviews**
    - Make requested changes
    - Push updates to your branch
    - Comment on resolved conversations

2. **Final Approval**
    - Wait for maintainer approval
    - Address any final comments

## Step 8: Celebrate!

Once your PR is merged:
- You're now an open source contributor!
- Add yourself to the contributors list
- Share your achievement on social media

## Troubleshooting

### Common Issues

1. **Tests Fail**  
   ```bash  
   poetry run pytest -v  
   ```
    - Check test files for examples

2. **Merge Conflicts**  
   ```bash  
   git fetch upstream  
   git rebase upstream/main
# Resolve conflicts, then:
git rebase --continue  
```

3. **Code Style Issues**  
   ```bash  
   poetry run black .  
   ```
    - Check [style guide](CONTRIBUTING.md#style-guide)

## Next Steps

- Join our [Discord](https://discord.gg/YOUR_INVITE_CODE) for real-time help
- Explore more issues to contribute to
- Consider becoming a regular contributor

Welcome to the open source community!  