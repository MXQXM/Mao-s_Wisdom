import os
from typing import Dict, List

import httpx


def invoke_local_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    model_config: Dict,
) -> str:
    """调用 LLM (OpenAI 兼容 API)。

    用裸 httpx 而非 OpenAI SDK: SDK 在 Windows + asyncio 线程池(LangGraph节点)
    中有连接建立问题(慢/失败), 裸 httpx 线程内稳定 (实测 1.0s)。
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY / OPENAI_API_KEY / LLM_API_KEY")

    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or os.getenv("LLM_BASE_URL")
    if not base_url:
        base_url = "https://api.deepseek.com"   # 默认 DeepSeek 官方
    model = os.getenv("MODEL_NAME") or os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL")
    if not model and str(model_config.get("model", "")).startswith("doubao-"):
        model = "deepseek-v4-flash"   # Coze 模板的 doubao 占位 -> DeepSeek v4 flash
    model = model or model_config.get("model")
    if not model:
        model = "deepseek-v4-flash"   # 最终兜底

    max_tokens = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "4000"))
    cfg_maxtok = int(model_config.get("max_completion_tokens", 0) or 0)
    max_tokens = max(max_tokens, cfg_maxtok)   # 取环境变量与配置的较大值

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    timeout = float(os.getenv("LOCAL_LLM_TIMEOUT", "180"))

    # 1) 本机 Ollama: /api/chat 原生协议
    if "11434" in base_url:
        chat_url = base_url.rstrip("/").removesuffix("/v1") + "/api/chat"
        response = httpx.post(
            chat_url,
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "think": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=timeout,
            trust_env=False,   # 不走系统代理(Windows代理会拦localhost->502)
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    # 2) OpenAI 兼容 API (DeepSeek 等): 跟随系统代理(用户Clash规则模式国内直连正常;
    #    强制直连反而在代理开启时被拦 -> SSL超时; 代理关闭时自然直连)
    url = base_url.rstrip("/").removesuffix("/v1") + "/v1/chat/completions"
    body: Dict = {
        "model": model,
        "messages": messages,
        "temperature": model_config.get("temperature", 0.2),
        "top_p": model_config.get("top_p", 0.7),
        "max_tokens": max_tokens,
        "stream": False,
    }
    if "deepseek" in base_url:
        body["thinking"] = {"type": "disabled"}   # v4系列关闭思考, 防审稿过程外泄+提速

    # 双通道自适应: 用户Clash开关状态不定 -> 代理/直连都试, 先走代理(代理开时必通)
    last_err = None
    for trust_env in (True, False):
        try:
            response = httpx.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=timeout,
                trust_env=trust_env,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            # v4-flash 有时把内容放 reasoning_content, content 为空 -> 双保险读取
            return message.get("content") or message.get("reasoning_content") or ""
        except Exception as e:
            last_err = e
    raise last_err
