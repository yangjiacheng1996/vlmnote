#!/usr/bin/env python

import logging
import traceback
import time
import json
import openai

from py3lib.logsystem import logger


class OpenAICompatible:
    
    """OpenAI库函数封装"""

    def __init__(self, base_url:str, api_key: str, model_name: str, temperature: float = 0.7, max_tokens: int = 8000, timeout: int = 300):
        """
        初始化API客户端
        :param base_url: API基础URL
        :param api_key: API密钥
        :param model_name: 模型名称
        :param temperature: 温度参数
        :param max_tokens: 最大token数
        :param timeout: 超时时间(秒)
        """
        # 获取logger
        self.logger = logger
        # 连接大模型供应商
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        # 用户自定义模型名、温度、上下文窗口大小
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        # 验证用户配置是否有效，包括base_url, api_key, model_name.有一些供应商没有提供模型列表/v1/models，所以配置检测跳过。
        # self._validate_configuration()
        # 测试模型是否可用
        self._test_model_availability()


    def get_available_models(self):
        """获取供应商的所有可用模型的ID列表"""
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            raise RuntimeError(f"获取模型列表失败: {str(e)}")


    def _validate_configuration(self):
        """验证API配置和模型名称是否有效"""
        try:
            # 获取所有可用模型（这会触发实际的API调用，验证连接和API Key）
            available_models = self.get_available_models()
            
            # 检查传入的模型名称是否在可用列表中
            if self.model_name not in available_models:
                # 获取最接近的模型建议
                suggestions = []
                for model in available_models:
                    if self.model_name.lower() in model.lower():
                        suggestions.append(model)
                
                # 生成错误信息
                error_msg = f"模型 '{self.model_name}' 不存在。"
                if suggestions:
                    error_msg += f" 可能是您想使用: {', '.join(suggestions[:3])}"
                error_msg += f"\n可用模型列表: {', '.join(available_models[:5])} (等更多)"
                
                raise ValueError(error_msg)
                
        except Exception as e:
            self.logger.error(f"验证API配置失败: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise ValueError(f"验证API配置失败: {str(e)}")
    

    def _test_model_availability(self):
        """主动测试模型是否可用（可选的额外验证）"""
        try:
            # 发送一个简单的测试请求
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                temperature=0.1
            )
            return True
        except Exception as e:
            self.logger.error(f"模型 {self.model_name} 测试失败: {str(e)}")
            return False


    def chat_completion(self, prompt: str, retry: int = 3):
        """
        调用聊天补全API，返回流式响应,非sse格式

        :param prompt: 提示词
        :param retry: 重试次数，默认为3
        :return: API响应生成器,仅返回大模型回答的内容，不包含sse流式响应的格式。
        举例：你好，你是谁？ -> 你好，我是由深度求索公司研发的大语音模型。
        :raises: Exception API调用失败时抛出异常
        """
        for attempt in range(retry):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True
                )

                # 返回生成器而不是累积内容，保持流式处理
                for chunk in response:
                    # 对响应内容进行过滤
                    if not getattr(chunk, 'choices', None):
                        continue
                    if len(chunk.choices) == 0:
                        continue
                    if not hasattr(chunk.choices[0], 'delta'):
                        self.logger.warning("choices[0]中缺少delta字段")
                        continue
                    if not chunk.choices[0].delta.content:
                        continue
                    if chunk.choices[0].delta.content =="\n\n":
                        continue
                    #yield chunk
                    yield chunk.choices[0].delta.content

                # 如果成功生成所有块，则跳出重试循环
                return

            except openai.APITimeoutError:
                self.logger.warning(f"API超时，将在6秒后重试（{attempt +1}/{retry}）")
                if attempt < retry - 1:
                    time.sleep(6)
            except openai.APIError as e:
                self.logger.error(f"API错误: {str(e)}")
                if attempt < retry - 1:
                    self.logger.warning(f"将在6秒后重试（{attempt +1}/{retry}）")
                    time.sleep(6)
                else:
                    raise
            except Exception as e:
                self.logger.error(f"API调用失败: {str(e)}")
                if attempt < retry - 1:
                    self.logger.warning(f"将在6秒后重试（{attempt +1}/{retry}）")
                    time.sleep(6)
                else:
                    raise

        raise ValueError("API返回空响应")
    
    
    def sse_chat_completion(self, prompt: str, return_sse_dict: bool = True, retry: int = 3):
        """
        调用聊天补全API，返回流式响应,标准sse格式，以 data: 开头

        :param prompt: 提示词
        :param return_sse_dict: 默认是Ture，返回sse流式字典的json字符串形式。
            如果是False，则在标准sse格式的字符串的基础上，添加data: \n\n的外壳。
        :param retry: 重试次数，默认为3
        :return: API响应生成器,返回标准sse格式的回答。
        举例：你好，你是谁？ -> 你好，我是由深度求索公司研发的大语音模型。
        :raises: Exception API调用失败时抛出异常
        """
        for attempt in range(retry):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True
                )

                # 返回生成器而不是累积内容，保持流式处理
                for chunk in response:
                    # 对响应内容进行过滤
                    if not getattr(chunk, 'choices', None):
                        continue
                    if len(chunk.choices) == 0:
                        continue
                    if not hasattr(chunk.choices[0], 'delta'):
                        self.logger.warning("choices[0]中缺少delta字段")
                        continue
                    if not chunk.choices[0].delta.content:
                        continue
                    if chunk.choices[0].delta.content =="\n\n":
                        continue
                    # 对大模型返回内容进行过滤后，构造流式响应的标准格式字典
                    chunk_dict = {
                        "id": chunk.id,  
                        "object": "chat.completion.chunk",  
                        "created": chunk.created,  # 创建时间戳
                        "model": chunk.model,  # 使用的模型
                        "choices": [
                            {
                                "index": chunk.choices[0].index,
                                "delta": {
                                    "content": chunk.choices[0].delta.content
                                },
                                "logprobs": chunk.choices[0].logprobs,
                                "finish_reason": chunk.choices[0].finish_reason
                            }
                        ]
                    }
                    # 使用json.dumps进行序列化
                    json_str = json.dumps(chunk_dict, ensure_ascii=False)
                    # 返回格式控制。
                    if return_sse_dict:
                        yield json_str
                    else:
                        yield f"data: {json_str}\n\n"
                # 最后一个块结束后，发送一个空块，表示流式响应结束
                if return_sse_dict:
                    yield "[DONE]"
                else:
                    yield f"data: [DONE]\n\n"

                # 如果成功生成所有块，则跳出重试循环
                return

            except openai.APITimeoutError:
                self.logger.warning(f"API超时，将在6秒后重试（{attempt +1}/{retry}）")
                if attempt < retry - 1:
                    time.sleep(6)
            except openai.APIError as e:
                self.logger.error(f"API错误: {str(e)}")
                if attempt < retry - 1:
                    self.logger.warning(f"将在6秒后重试（{attempt +1}/{retry}）")
                    time.sleep(6)
                else:
                    raise
            except Exception as e:
                self.logger.error(f"API调用失败: {str(e)}")
                if attempt < retry - 1:
                    self.logger.warning(f"将在6秒后重试（{attempt +1}/{retry}）")
                    time.sleep(6)
                else:
                    raise

        raise ValueError("API返回空响应")

if __name__ == "__main__":
    base_url = "https://api.siliconflow.cn"
    api_key = "sk-psggkotzdnaurduuivmqteqzimlgetzisdgdhvvzmfhzkxop"
    model_name = "Pro/deepseek-ai/DeepSeek-V3.2"
    client = OpenAICompatible(base_url=base_url, api_key=api_key, model_name=model_name)
    prompt = "你好，你是谁？"
    for answer in client.chat_completion(prompt):
        print(answer,end="")  
    # 上方生成器返回结果如下：
    """
    你好！我是DeepSeek，由深度求索公司创造的AI助手。
    """
    print("-" * 50)
    for answer in client.sse_chat_completion(prompt):
        print(answer,end="")
    # 上方这个生成器，返回每行结果如下：
    """
    {"id": "019bf97338bd17e3aef4fd9f9e87a19c", "object": "chat.completion.chunk", 
    "created": 1769416636, "model": "Pro/deepseek-ai/DeepSeek-V3.2", 
    "choices": [{"index": 0, "delta": {"content": "ppt"}, "logprobs": null, "finish_reason": null}]}
    """
    print("-" * 50)
    for answer in client.sse_chat_completion(prompt, return_sse_dict=False):
        print(answer,end="")
    # 上方这个生成器，返回每行结果如下：
    """
    data: {"id": "019bf97354139eed78e6a6283aa63b8c", "object": "chat.completion.chunk", "created": 1769416643, "model": "Pro/deepseek-ai/DeepSeek-V3.2", 
    "choices": [{"index": 0, "delta": {"content": "你好"}, "logprobs": null, "finish_reason": null}]}

    """
        