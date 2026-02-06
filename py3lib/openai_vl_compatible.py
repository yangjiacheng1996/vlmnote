#!/usr/bin/env python

import logging
import traceback
import time
import json
import base64
import os
import openai

from py3lib.logsystem import logger
from py3lib.openai_compatible import OpenAICompatible


class OpenAIVLCompatible(OpenAICompatible):
    
    """OpenAI视觉语言模型(VLM)库函数封装"""

    def __init__(self, base_url: str, api_key: str, model_name: str, temperature: float = 0.7, max_tokens: int = 8000, timeout: int = 300):
        """
        初始化VLM API客户端
        :param base_url: API基础URL
        :param api_key: API密钥
        :param model_name: 模型名称
        :param temperature: 温度参数
        :param max_tokens: 最大token数
        :param timeout: 超时时间(秒)
        """
        super().__init__(base_url, api_key, model_name, temperature, max_tokens, timeout)


    def _encode_image(self, image_path: str) -> str:
        """
        将本地图片编码为base64字符串
        
        :param image_path: 图片的绝对路径
        :return: base64编码的图片字符串
        :raises: FileNotFoundError, IOError
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 获取文件扩展名，确定mime类型
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }.get(ext, 'image/jpeg')  # 默认使用jpeg
        
        with open(image_path, "rb") as image_file:
            base64_encoded = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:{mime_type};base64,{base64_encoded}"


    def _process_image_input(self, image_input):
        """
        处理图片输入，支持单张图片路径或图片路径列表
        
        :param image_input: 可以是单张图片路径(str)、图片路径列表(list)、或已编码的base64字符串
        :return: 图片内容列表，每个元素是base64编码的图片字符串
        """
        # 如果是字符串，转换为列表
        if isinstance(image_input, str):
            image_list = [image_input]
        elif isinstance(image_input, list):
            image_list = image_input
        else:
            raise TypeError("image_path 必须是字符串或字符串列表")
        
        # 处理每张图片
        result = []
        for img in image_list:
            # 如果已经是base64格式（以 data: 开头），直接使用
            if isinstance(img, str) and img.startswith('data:'):
                result.append(img)
            # 如果是本地图片路径，进行编码
            elif isinstance(img, str) and os.path.exists(img):
                result.append(self._encode_image(img))
            else:
                raise ValueError(f"无效的图片输入: {img}")
        
        return result


    def sse_vlm_chat(self, image_paths, prompt: str, return_sse_dict: bool = True, retry: int = 3):
        """
        调用VLM聊天补全API，返回流式响应
        
        :param image_paths: 图片路径，支持三种格式：
            - 单张图片路径（str）
            - 图片路径列表（list），每个元素是图片路径或已编码的base64字符串
        :param prompt: 提示词
        :param return_sse_dict: 默认是True，返回sse流式字典的json字符串形式。
            如果是False，则在标准sse格式的字符串的基础上，添加data: \n\n的外壳。
        :param retry: 重试次数，默认为3
        :return: API响应生成器,返回标准sse格式的回答。
        举例：描述这些图片 -> 这是一张卡通风格的图片...
        :raises: Exception API调用失败时抛出异常
        """
        for attempt in range(retry):
            try:
                # 处理图片输入，支持单张或多张
                image_contents = self._process_image_input(image_paths)
                
                # 构建消息内容，首先添加文本
                content_list = [{"type": "text", "text": prompt}]
                
                # 添加所有图片
                for img_content in image_contents:
                    content_list.append({
                        "type": "image_url",
                        "image_url": {
                            "url": img_content
                        }
                    })
                
                # 构建消息
                messages = [
                    {
                        "role": "user",
                        "content": content_list
                    }
                ]
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
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
                    if chunk.choices[0].delta.content == "\n\n":
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
                self.logger.error(traceback.format_exc())
                if attempt < retry - 1:
                    self.logger.warning(f"将在6秒后重试（{attempt +1}/{retry}）")
                    time.sleep(6)
                else:
                    raise

        raise ValueError("API返回空响应")


if __name__ == "__main__":
    base_url = "https://api.siliconflow.cn"
    api_key = "sk-psggkotzdnaurduuivmqteqzimlgetzisdgdhvvzmfhzkxoo"
    model_name = "Qwen/Qwen3-VL-235B-A22B-Thinking"
    
    client = OpenAIVLCompatible(base_url=base_url, api_key=api_key, model_name=model_name)
    
    # 测试单张图片
    image_path = "/config/workspace/llmnote/workspace/过期米老鼠/frames/frame00.00.01-0.jpg"
    prompt = "请描述这张图片的内容"
    
    print("=" * 50)
    print("测试VLM单张图片描述功能")
    print("=" * 50)
    print(f"图片路径: {image_path}")
    print(f"提示词: {prompt}")
    print("-" * 50)
    
    print("流式响应结果：")
    for answer in client.sse_vlm_chat(image_path, prompt, return_sse_dict=True):
        if answer == "[DONE]":
            break
        try:
            chunk = json.loads(answer)
            content = chunk["choices"][0]["delta"]["content"]
            print(content, end="")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"解析响应块失败: {e}")
    
    print("\n" + "=" * 50)
    
    # 测试多张图片
    image_paths = [
        "/config/workspace/llmnote/workspace/过期米老鼠/frames/frame00.00.01-0.jpg",
        "/config/workspace/llmnote/workspace/过期米老鼠/frames/frame00.00.02-0.41.jpg"
    ]
    prompt = "请比较这两张图片的异同"
    
    print("测试VLM多张图片比较功能")
    print("=" * 50)
    print(f"图片路径列表: {image_paths}")
    print(f"提示词: {prompt}")
    print("-" * 50)
    
    print("流式响应结果：")
    for answer in client.sse_vlm_chat(image_paths, prompt, return_sse_dict=True):
        if answer == "[DONE]":
            break
        try:
            chunk = json.loads(answer)
            content = chunk["choices"][0]["delta"]["content"]
            print(content, end="")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"解析响应块失败: {e}")
    
    print("\n" + "=" * 50)
    print("测试完成")
