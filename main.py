
import os

from dotenv import load_dotenv
import discord

from src.discordBot import DiscordClient, Sender
from src.logger import logger
from src.chatgpt import ChatGPT, DALLE
from src.models import OpenAIModel
from src.memory import Memory
from src.server import keep_alive
import datetime

# 创建一个字典来存储用户的使用记录和限制信息
user_records = {}

load_dotenv()

models = OpenAIModel(api_key=os.getenv('OPENAI_API'), model_engine=os.getenv('OPENAI_MODEL_ENGINE'))

memory = Memory(system_message=os.getenv('SYSTEM_MESSAGE'))
chatgpt = ChatGPT(models, memory)
dalle = DALLE(models)


def run():
    client = DiscordClient()
    sender = Sender()

    @client.tree.command(name="chat", description="Have a chat with ChatGPT")
    async def chat(interaction: discord.Interaction, *, message: str):
        user_id = interaction.user.id
        if interaction.user == client.user:
            return
        await interaction.response.defer()
        try:
            if check_user_limit(user_id, 10):
                receive = chatgpt.get_response(user_id, message)
                await sender.send_message(interaction, message, receive)
            else:
                await interaction.followup.send('> Reached the daily limit of 10 uses <')
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            await interaction.followup.send('> Oops! Something went wrong. <')
    

    # @client.tree.command(name="imagine", description="Generate image from text")
    # async def imagine(interaction: discord.Interaction, *, prompt: str):
    #     if interaction.user == client.user:
    #         return
    #     await interaction.response.defer()
    #     image_url = dalle.generate(prompt)
    #     await sender.send_image(interaction, prompt, image_url)

    @client.tree.command(name="reset", description="Reset ChatGPT conversation history")
    async def reset(interaction: discord.Interaction):
        user_id = interaction.user.id
        logger.info(f"resetting memory from {user_id}")
        try:
            chatgpt.clean_history(user_id)
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(f'> Reset ChatGPT conversation history < - <@{user_id}>')
        except Exception as e:
            logger.error(f"Error resetting memory: {e}")
            await interaction.followup.send('> Oops! Something went wrong. <')

    client.run(os.getenv('DISCORD_TOKEN'))


def check_user_limit(user_id, limit):
    # 获取当前日期
    today = datetime.date.today()

    # 检查用户ID是否存在于记录中
    if user_id in user_records:
        last_date, count = user_records[user_id]

        # 检查最后一次使用的日期是否与当前日期相同
        if last_date == today:
            # 如果日期相同，将使用次数加1
            count += 1
        else:
            # 如果日期不同，将使用次数重置为1
            count = 1
    else:
        # 如果用户ID不存在于记录中，将其添加到记录中，并将使用次数设置为1
        count = 1

    # 更新用户记录
    user_records[user_id] = (today, count)

    # 检查使用次数是否超过限制
    if count > limit:
        return False
    else:
        return True
    
if __name__ == '__main__':
    keep_alive()
    run()
