# Fava Budget Freedom

Fava Budget Freedom 是一个 [Fava](https://beancount.github.io/fava/) 的扩展插件，旨在提供更灵活、强大的预算管理和可视化功能。它支持基于通配符的账户匹配、多种预算周期以及预算滚存（Rollover）机制，帮助你更好地实现财务自由。

## 主要特性

- **灵活的预算定义**：使用自定义指令定义预算，支持通配符（如 `Expenses:Food:*`）。
- **多种周期支持**：支持 `monthly`（月度）、`weekly`（周度）、`quarterly`（季度）和 `yearly`（年度）预算。
- **预算滚存 (Rollover)**：支持月度预算的滚存功能，上月未用完的额度自动累积到下月，超支则扣减下月额度。
- **可视化进度条**：直观展示预算使用进度，并根据时间进度显示理想参考线（仅限整年视图）。
- **智能时间范围**：支持 Fava 的时间筛选，默认显示今年至今（YTD）的预算执行情况。
- **交互式报表**：点击账户模式可直接跳转到对应的账户详情页面。

## 使用方法

### 1. 安装插件

确保 `fava_budget_freedom` 目录在你的 Python 路径中。

### 2. 配置 Beancount

在你的 `.beancount` 文件中加载插件：

```beancount
2025-01-01 custom "fava-extension" "fava_budget_freedom"
```

### 3. 定义预算

使用 `custom "budget"` 指令定义预算。

**语法：**

```beancount
YYYY-MM-DD custom "budget" "AccountPattern" "Amount Currency" "Period" ["rollover"]
```

- **AccountPattern**: 账户名称或通配符模式（例如 `Expenses:Food` 或 `Expenses:Food:*`）。
- **Amount Currency**: 预算金额和货币（例如 `2000 CNY`）。
- **Period**: 预算周期，可选值：`monthly`, `weekly`, `quarterly`, `yearly`。
- **rollover**: (可选) 仅适用于 `monthly`，开启后支持预算累积。

**示例：**

```beancount
; 每月餐饮预算 2000 USD，开启滚存
2025-01-01 custom "budget" "Expenses:Food:*" "2000 USD" "monthly" "rollover"

; 每周书籍预算 20 EUR
2025-01-01 custom "budget" "Expenses:Books" "20.00 EUR" "weekly"

; 年度旅行预算 2500 EUR
2025-01-01 custom "budget" "Expenses:Holiday" "2500.00 EUR" "yearly"
```

## 开发与启动

### 环境准备

建议使用 Python 虚拟环境进行开发，以避免污染系统环境。

1.  **创建虚拟环境**

    ```bash
    python3 -m venv venv
    ```

2.  **激活虚拟环境**

    - macOS / Linux:
      ```bash
      source venv/bin/activate
      ```
    - Windows:
      ```bash
      venv\Scripts\activate
      ```

3.  **安装依赖**

    ```bash
    pip install fava beancount
    ```

### 启动项目

在本地开发环境中，可以使用提供的示例文件进行测试。

1.  设置 `PYTHONPATH` 为当前目录，以便 Fava 能加载插件。
2.  启动 Fava。

```bash
# 设置 PYTHONPATH 并启动 Fava
export PYTHONPATH=$PWD
fava example.beancount
```

或者直接运行：

```bash
PYTHONPATH=. fava example.beancount
```

访问 `http://localhost:5000` 并在侧边栏中找到 "Budget Freedom" 扩展页面。
