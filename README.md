# This is sticking around for posterity but... 
...in this day and age you're better off with Nanoclaw or Openclaw. 

I've personally moved to Claude Code and Nanoclaw.

I got into this project at the release of GPT3 and it's what got me started coding and working with AI.

💗

## Wheatley Discord Bot (ChatGPT backed OpenAI API bot to be precise GPT4o, 4omini, groq, lm-studio modes available)

## What is this?

Welcome to the Wheatley Discord Bot! This bot is designed to provide you with informative results from the web within the comfort of the Discord interface. With Wheatley, you can search Google, generate images based on your prompt, or just chat.

Bring ChatGPT/Groq/your local LLM with you everywhere via Discord.

I have a persona for Wheatley (the funny ai in Portal 2 voiced by Stephen Merchant) but you are free to easily just change the variable to whatever persona you want.

## Disclaimer - I am not a programmer by trade! 
- I am learning as I go. I've used chatgpt to help me write this bot and now I just use this bot to help me write this bot.
- my code is probably a garbled mess though I do try to comment it nicely. chatgpt has helped me get to a working bot much faster than I should have so I'm sure I've skipped basic training as it were.
- I'm aware this is not pristine, but it works and it's fun and is an incredible learning experience for me
- feel free to give me pointers if you are just so appaled you can't stay quiet :) constructive criticism is always welcome, I may or may not have time to act on it.
- recently I have included a .env to help with variable setup, and a botFunctions.py to store some lengthy functions to help clean it up a lot

## github file explanation

- wheatleyDiscord.py - the main bot, gpt3.5, 4, lm-studio (if you have that setup), groq, lots of functions, !help once he's up explains them all
- requirements.txt - list of librarys, can be installed once you have python up and running with pip install -r requirements.txt
- .envexample - enter all your necessary apis/variables here then RENAME to .env
- botFunctions - holds some lengthy functions just to keep main script kind of clean

## Requirements

- OpenAI API key OR Groq API key OR lmstudio running on your own machine

## Optional 'requirements'

- free Google API Search key and engine ID code - optional but highly recommended to use the !search feature, 
- get your engine code here, click 'add' and follow the process: https://support.google.com/programmable-search/answer/12499034?hl=en-GB&ref_topic=4513743
- Google Api Key : [https://developers.google.com/webmaster-tools/search-console-api/v1/configure](https://support.google.com/googleapi/answer/6158862?hl=en#:~:text=To%20create%20your%20application%27s%20API%20key%3A%201%20Go,Click%20Create%20credentials%20and%20then%20select%20API%20key.)
- OpenAI API key - get an account from beta.openai.com/playground ensure billing is setup to increase your rate limits, generate an api key in settings
- python 3.10 at least
- then once python is installed, run pip install -r requirements.txt to install all the libraries needed
- a Discord Bot's token - created from the Discord Developer Portal, see below

## Discord Bot setup How To
- log in to Discord client and make yourself a server with just you in it
- log in to the Discord Developer Portal: [Discord Developer Portal](https://discord.com/developers)
- click Application at the left, and click New Application button on the right
- Name it, check the box, click create
- on the left hand side click 'Bot', then on the right 'Add Bot'
- click the 'copy' button to copy your token somewhere save, or directly into the variable at the top of the script
- uncheck 'public bot'
- check all three intents
- under OAuth2 check bot
- under bot permissions check all text permissions, (the whole middle row), then in the General column, select change nickname, read messages/ view channels
- now you'll see a link along the bottom has been generated, copy this link in a new tab and click it to add your bot to your server
- fill in all the api keys etc at the top of the script and start your bot on your local computer
- once started your bot will come online in your channel and you can start talking to it!

## Features

Usage:

💬Feel free to start chatting!
🙏Done with the conversation? Just say 'thanks' somewhere in your message. To reset your tokens.
🔎Need current info? Say the words 'search' and 'please' somewhere in your message. (requires google api key and engine setup)
🖼️Want a picture or four? Mention the word 'picture' or 'image' and 'generate'  in your message and describe what you'd like to see, as well as how many.
📲If you want to see more commands, just type !help
🤖AI Models Available: 
- !gpt3 - GPT-3.5-Turbo
- !gpt4 - GPT-4-Turbo
- !llm - {lmStudioModel}
- !groq - llama 3 70B

Summarize youtube videos or web articles
- just paste ONLY the URL in the chat and press enter
- This is a SUPER useful feature, I use it multiple times a day. It uses many tokens so best paired with lmstudio to do the summarizing for free locally

File management:

- There is no command here, just drop a text file in as an attachment, include a prompt within that file. The bot will respond within an attachment that it sends back to you. In this manner you can get around the 2000 word limit of discord. Especially useful when you want a massive prompt/response from GPT4.


## Getting Started

This is not a public bot. You are to copy the code and input your own API keys and pull it into a private discord server. There is no threading or anything setup so it can only handle one person/conversation at a time.

By default, the bot is named Wheatley with the same identity. However, you are free to change his identity by creating a new persona in the main code.

## Usage

Make liberal use of the thanks command to keep wiping history to save you api $$. 

Wheatley responds to any message posted in your server, he's currently designed for personal server use only because of this fact. It makes him much easier to talk to versus needing to make a thread everytime or mention him.
