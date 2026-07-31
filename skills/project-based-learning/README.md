# project-based-learning-skill

这是一个 Codex skill，用于按照 project-based learning 的方式学习编程项目。

它会让 Codex 先理解 README、代码结构、依赖、构建流程和运行行为，然后用中文一步步讲解基础知识、代码含义和练习检查点。

## Ubuntu 安装

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/longly-ctrl/project-based-learning-skill.git ~/.agents/skills/project-based-learning
```

如果已经安装过，更新用：

```bash
cd ~/.agents/skills/project-based-learning
git pull
```

## 使用方式

重启 Codex 后，可以这样调用：

```text
Use $project-based-learning to 列出 C++ 里适合初学者的项目。
```

或者：

```text
Use $project-based-learning to 教我学习 Beginning Game Programming with C++ and SDL。
```

## 教学方式

- 默认使用中文讲解。
- 先讲项目目标和需要的基础知识。
- 不死板照读 README，而是理解项目后再讲解。
- 默认让学习者自己一步步写代码。
- 每次只给一个小步骤、一个小代码块或一个命令。
- 学习者运行后，再继续下一步。