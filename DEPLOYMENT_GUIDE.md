# 生产环境部署与维护指南 (Ubuntu)

本文档为在 Ubuntu 服务器上部署和维护本 AI Agent 项目的标准作业流程 (SOP)。

## 1. 首次部署流程

本流程将引导您从零开始，完成应用的首次部署，并将其配置为一个稳定运行的后台服务。

### 第 1 步：环境准备

1.  **克隆代码库**
    如果您尚未完成，请将项目克隆到您的用户主目录。
    ```bash
    # 该目录将作为后续所有操作的工作目录
    cd ~
    git clone <您的项目git地址> ykn_agent/ykn-agent-chatbot
    ```

2.  **进入项目目录**
    ```bash
    cd ~/ykn_agent/ykn-agent-chatbot
    ```

### 第 2 步：安装与配置数据库 (PostgreSQL)

1.  **安装 PostgreSQL**
    ```bash
    sudo apt update
    sudo apt install postgresql postgresql-contrib
    ```

2.  **启动并设置开机自启**
    ```bash
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    ```

3.  **创建数据库和用户**
    进入 PostgreSQL shell：
    ```bash
    sudo -u postgres psql
    ```
    执行以下 SQL 命令，请务必将 `your_strong_password_here` 替换为一个强密码：
    ```sql
    CREATE DATABASE ykn_agent_db;
    CREATE USER ykn_agent_user WITH ENCRYPTED PASSWORD 'your_strong_password_here';
    GRANT ALL PRIVILEGES ON DATABASE ykn_agent_db TO ykn_agent_user;
    \q
    ```

### 第 3 步：配置应用程序

1.  **安装项目依赖**
    ```bash
    # 确保在项目根目录下
    uv sync
    ```

2.  **创建生产环境配置文件**
    ```bash
    cp .env.example .env.production
    ```

3.  **编辑配置文件**
    使用您喜欢的编辑器（如 nano）打开该文件：
    ```bash
    nano .env.production
    ```
    至少需要更新以下内容：
    - `POSTGRES_URL`: 修改为您在第 2 步中创建的数据库连接信息。
      ```
      POSTGRES_URL="postgresql://ykn_agent_user:your_strong_password_here@localhost:5432/ykn_agent_db"
      ```
    - 填入所有必需的 API 密钥，例如 `OPENAI_API_KEY`, `LANGFUSE_SECRET_KEY` 等。

### 第 4 步：创建 systemd 后台服务

为了让应用能在后台稳定运行，并能开机自启，我们将其创建为一个 `systemd` 服务。

1.  **创建服务文件**
    ```bash
    sudo nano /etc/systemd/system/ykn-agent.service
    ```

2.  **粘贴服务配置**
    将以下为您定制的配置内容**完整**复制并粘贴到编辑器中。

    ```ini
    [Unit]
    # 服务描述
    Description=YKN Agent Chatbot Service
    # 确保在网络和数据库服务启动后才启动本服务
    After=network.target postgresql.service

    [Service]
    # 运行服务的用户和组 (根据您系统确认)
    User=lgdx
    Group=lgdx

    # 项目的根目录
    WorkingDirectory=/home/lgdx/ykn_agent/ykn-agent-chatbot

    # 启动服务的具体命令 (使用 which make 确认路径)
    ExecStart=/usr/bin/make production

    # 指定加载的环境变量文件
    EnvironmentFile=/home/lgdx/ykn_agent/ykn-agent-chatbot/.env.production

    # 配置服务在失败时自动重启
    Restart=always
    RestartSec=10

    [Install]
    # 定义服务在哪个运行级别下启用
    WantedBy=multi-user.target
    ```

3.  **保存并退出**
    按下 `Ctrl+X`，然后按 `Y`，最后按 `Enter`。

### 第 5 步：启动并验证服务

1.  **重载 systemd 配置**，使其识别新创建的服务。
    ```bash
    sudo systemctl daemon-reload
    ```

2.  **启动应用服务**
    ```bash
    sudo systemctl start ykn-agent.service
    ```

3.  **设置开机自启**
    ```bash
    sudo systemctl enable ykn-agent.service
    ```

4.  **验证服务状态**
    ```bash
    sudo systemctl status ykn-agent.service
    ```
    如果看到绿色的 `active (running)` 字样，代表部署成功！

---

## 2. 代码更新流程

当您需要更新服务器上的代码时，请遵循以下流程。

### 为什么需要重启？
生产环境下的服务启动后，会将代码加载到内存中执行，不会自动监听文件的变化。因此，任何代码改动后，都必须重启服务以加载新代码。

### 标准更新三步曲

1.  **拉取最新代码**
    进入项目目录，从 Git 拉取最新版本。
    ```bash
    cd ~/ykn_agent/ykn-agent-chatbot
    git pull
    ```

2.  **同步项目依赖** (好习惯)
    更新依赖库，以确保与新代码兼容。
    ```bash
    uv sync
    ```

3.  **重启应用服务**
    这是最关键的一步，`systemd` 会用新代码重启您的应用。
    ```bash
    sudo systemctl restart ykn-agent.service
    ```

### 更新后验证

重启后，建议花几秒钟检查服务状态，确保新代码没有引入问题。
```bash
# 检查服务是否正常运行
sudo systemctl status ykn-agent.service

# 如果启动失败，查看日志以定位问题
sudo journalctl -u ykn-agent.service -n 100 --no-pager
```

---

## 附录：常用命令备忘录

| 命令                                                | 描述                     |
| --------------------------------------------------- | ------------------------ |
| `sudo systemctl start ykn-agent.service`            | 启动服务                 |
| `sudo systemctl stop ykn-agent.service`             | 停止服务                 |
| `sudo systemctl restart ykn-agent.service`          | 重启服务                 |
| `sudo systemctl status ykn-agent.service`           | 查看服务状态             |
| `sudo systemctl enable ykn-agent.service`           | 设置开机自启             |
| `sudo systemctl disable ykn-agent.service`          | 取消开机自启             |
| `sudo journalctl -u ykn-agent.service -f`           | 查看实时日志             |
| `sudo journalctl -u ykn-agent.service -n 200`       | 查看最新的 200 条日志    | 