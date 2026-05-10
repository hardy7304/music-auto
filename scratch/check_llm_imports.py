try:
    from browser_use import ChatOpenAI
    print("ChatOpenAI found in browser_use")
except ImportError:
    print("ChatOpenAI NOT found in browser_use")

try:
    from browser_use.llm.openai.chat import ChatOpenAI
    print("ChatOpenAI found in browser_use.llm.openai.chat")
except ImportError:
    print("ChatOpenAI NOT found in browser_use.llm.openai.chat")

try:
    import browser_use
    print(f"browser_use components: {dir(browser_use)}")
    import browser_use.llm
    print(f"browser_use.llm components: {dir(browser_use.llm)}")
except Exception as e:
    print(f"Error: {e}")
