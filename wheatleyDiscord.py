# This program is a Discord chatbot that can connect to OpenAI 's gpt3.5 and gpt4.0 APIs, as well as groq
# AND local lmstudio ai models and has access to a local comfyui install.
# you don't have to utilize all these features, and can simply use it to chat to openai or groq
# however I highly recommend the google search feature, it's free as long as you stay under 100
# searches a day (note each search uses 3 searches)
# Fill in variables in .env
# Created Jan 2023
# Last updated Aug 2024
# Author Stavros


###
###  Type !help to see a list of commands once bot is up
###

#so many libraries to import
from openai import OpenAI
from groq import Groq
import os
import tiktoken
import requests
import discord
import asyncio
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from datetime import datetime
import base64
from PIL import Image
from io import BytesIO
import random
import socket
from youtube_transcript_api import YouTubeTranscriptApi
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
# Import required libraries for comfy
import websocket # NOTE: websocket-client library from GitHub (https://github.com/websocket-client/websocket-client)
import uuid      # For generating unique client IDs
import json      # For JSON handling
import urllib.request  # For making HTTP requests
import urllib.parse    # For URL encoding
from dotenv import load_dotenv
# needed for most functions specific to this bot -- housed in botFunctions.py in this same folder
import botFunctions
import database
#import botVariables
load_dotenv() #pull .env variables in

# Initialize the scheduler for timed messages
scheduler = AsyncIOScheduler()

# create a Discord client object with the necessary intents
intents = discord.Intents.all()
intents.members = True
client = discord.Client(intents=intents)

#timezone
time_zone = timezone(os.environ['time_zone'])

#set api keys and other variables (need to move this into a .env...)
openaiapikey = os.environ['OPENAI_API_KEY']
groqApiKey = os.environ['GROQ_API_KEY']
aiclient = OpenAI(api_key=openaiapikey)
discordBotToken = os.environ['discordBotToken']
googleApiKey = os.environ['googleApiKey']
googleEngineID = os.environ['googleEngineID']
location = os.environ['location']
weatherURL = os.environ['weatherURL']
comfyIP = os.environ['comfyIP']
comfyPort = os.environ['comfyPort']
lmstudioIP = os.environ['lmstudioIP']
lmstudioPort = os.environ['lmstudioPort']
notifications = int(os.environ['notifications'])

#model temperature, 0 is more precise answers, 1 is more creative, and you can use decimals
modelTemp = float(os.environ['modelTemp'])

#set defaul model
model = os.environ['model']
lmStudioModel = os.environ['lmStudioModel']
groqModel = os.environ['groqModel']

#default comfy image generation dimensions
w = os.environ['w']
h = os.environ['h']

#conversation history array
history = []

#habits
askingAboutHabits = 0
user_habit_data = {}


# Set up tokenizer
#declare global totals
totalCost = 0
totalTokens = 0
prompt_token_count = 0
fullDate =""
imgGenNum = 0
cleanedBotSearchGen = ""
searchFlag = 0
costing = "placeholder"

#setup !search variables
url1 = ""
url2 = ""
url3 = ""
url4 = ""

#summarizing verbage -- used currently for summarizing youtubes or articles
summarizeInstructions = """IDENTITY and PURPOSE
                    You are an expert Youtube Video summarizer. You take content in and output a Markdown formatted summary using the format below.

                    Take a deep breath and think step by step about how to best accomplish this goal using the following steps.

                    OUTPUT SECTIONS
                    Include the video Title as the first item.
                    If an article's title contains a question or has a clickbait-like tone, promptly provide the answer to that title directly below it.

                    Combine all of your understanding of the content into a summary paragraph in a section called Summary:.

                    Output the 10 most important points of the content as a list with no more than 15 words per point into a section called Main Points:.

                    Output a list of the 5 best takeaways from the content in a section called Takeaways:.

                    If there are any useful quotes in the article, include them in a final section called Notable Quotes:.

                    OUTPUT INSTRUCTIONS
                    Create the output using the formatting above.
                    You only output human readable Markdown.
                    Output numbered lists, not bullets.
                    Do not output warnings or notes—just the requested sections.
                    Do not repeat items in the output sections.
                    Do not start items with the same opening words.
                    
                    INPUT:"""

summarizeArticle = """IDENTITY and PURPOSE
                    You are an expert article summarizer. You take content in and output a Markdown formatted summary using the format below.

                    Take a deep breath and think step by step about how to best accomplish this goal using the following steps.

                    OUTPUT SECTIONS
                    Include the article Title as the first item.
                    
                    If an article's title contains a question or has a clickbait-like tone, promptly provide the answer to that title directly below it.

                    Combine all of your understanding of the content into a summary paragraph in a section called Summary:.

                    Output the 10 most important points of the content as a list with no more than 15 words per point into a section called Main Points:.

                    Output a list of the 5 best takeaways from the content in a section called Takeaways:.

                    If there are any useful quotes in the article, include them in a final section called Notable Quotes:.

                    OUTPUT INSTRUCTIONS
                    Create the output using the formatting above.
                    You only output human readable Markdown.
                    Output numbered lists, not bullets.
                    Do not output warnings or notes—just the requested sections.
                    Do not repeat information as you go.
                    Do not start items with the same opening words.
                    
                    INPUT:"""

#!file variable
inputContent = ""
outputFile = "outputFile.txt"

#variables needed for comfyui image creation
image = ""
randomNum = random.randint(1000,9999)

#provide the year day and date so he's aware and then jam that into the history variable
def setSystemPrompt():
    global fullDate, location, identity, wheatley, ghistory
    now = datetime.now()
    year = now.year
    month = now.strftime("%B")
    day = now.strftime("%A")
    dayOfMo = now.day
    time = now.strftime("%H:%M:%S")
    fullDate = str(year) + " " + str(month) + " " + str(dayOfMo) + " " + str(day) + " " + str(time)
    wheatley = {"role": "system", "content": f"""Date: {fullDate} Location: {location}. 
                Your identity: You are a helpful and empathetic chat bot named Wheatley. Please respond to my message as effectively as you can. 
                Use an emoji in your response if you think it will add to readibility. 
                Use Markdown language to format your responses for improved readability.
                My identity: I am Steve. A friend of yours."""}
    history.append(wheatley)
    identity = wheatley

#calculating token numbers for token calculator
def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    number_tokens = 0
    for message in messages:
        number_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            number_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                number_tokens += -1  # role is always required and always 1 token
    number_tokens += 2  # every reply is primed with <im_start>assistant
    return number_tokens
    
#tokenizer costing function
#currently not in use, but just simply call it if needed with caluculateCost()
def calculateCost():
    global totalCost
    global totalTokens
    global history
    global prompt_token_count
    #calculate cost
    if (model == "gpt-4o-mini"):
        cost_per_token = 0.00015 / 1000  # $0.0015 for turbo3.5 16k per 1000 tokens
    elif (model == "gpt-4o"):
        cost_per_token = 0.02 / 1000  # $0.0015 for turbo3.5 16k per 1000 tokens
    elif (model == lmStudioModel or model == groqModel):
        cost_per_token = 0 / 1000  # $0.0015 for turbo3.5 16k per 1000 tokens
    totalTokens = num_tokens_from_messages(history) - 4
    totalCost = totalTokens * cost_per_token
    global costing
    costing = f"🪙 ${totalCost:.4f} -- 🎟️ Tokens {totalTokens}"
    #not currently printing this.

#function that takes the user input and sends it off to openai model specified
#and returns the bots response back to where it's called as the 'message' variable 
async def ask_openai(prompt, history):
    global num_tokens
    global prompt_token_count
    global model_max_tokens
    global model
    global aiclient
    # Generate user resp obj
    user_response_obj = {"role": "user", "content": prompt}
    history.append(user_response_obj)
    
    prompt_token_count = num_tokens_from_messages(history)
    response = aiclient.chat.completions.create(model=model, messages=history, temperature=modelTemp, stream=False)
    history.append({"role": "assistant", "content": response.choices[0].message.content})
    return str(response.choices[0].message.content)

async def stream_openai_multi(prompt, history, channel):
    global num_tokens
    global prompt_token_count
    global model
    global model_max_tokens
    global aiclient
    newMessage = 0
    fullMessage = ""
    full_reply_content = ""
    second_reply_content = ""
    collected_messages = []
    user_response_obj = {"role": "user", "content": prompt}
    history.append(user_response_obj)

    prompt_token_count = num_tokens_from_messages(history)
    #send the first message that will continually be editted
    #send the first message that will continually be editted
    model_to_emoji = {
    "gpt-4.1-nano": "🤔",
    lmStudioModel: "💭",
    "gpt-4.1": "🧠",
    groqModel: "🦙"
    }
    streamedMessage = await channel.send(model_to_emoji[model])


    #aiclient = OpenAI()
    response = aiclient.chat.completions.create(model=model, messages=history, temperature=modelTemp, stream=True)

    collected_messages = []
    second_collected_messages = []
    counter = 0
    current_message = ''
    #as long as there are messages comnig back from openai, do the for loop
    
    for data in response:
        for choice in data.choices:
            if choice.delta and choice.delta.content:
                content = choice.delta.content
                if content:
                    if newMessage == 0:
                        collected_messages.append(content)
                        full_reply_content = ''.join(collected_messages)
                        fullMessage = full_reply_content
                        counter += 1 # used to slow down how often chunks are actually printed/edited to discord
                    else: # we must be in the second message now so start adding chunks to the second message vars instead
                        second_collected_messages.append(content)
                        second_reply_content = ''.join(second_collected_messages)
                        counter += 1 # used to slow down how often chunks are actually printed/edited to discord
            
                if counter % 40 == 0: # when the number of chunks is divisible by 10 (so every 10) print to discord
                    if len(fullMessage) >= 1800:  # Check if message length is close to the Discord limit
                        if newMessage == 0: # if this is the first time it's been over...
                            await streamedMessage.edit(content=fullMessage) # complete the first message 
                            streamedMessage2 = await channel.send("...")  # create a blank message for the second message to stream into
                            newMessage = 1 # set the flag saying we're not onto the second message
                        else: # we must now be into the second message going forward now
                            await streamedMessage2.edit(content=second_reply_content) # update second message with the latest chunk
                        
                    else: # we are still in the first message so update first message normally
                        await streamedMessage.edit(content=full_reply_content)
                        # print(len(fullMessage)) # debug so I can watch when it's about to flip over
    if newMessage == 1: # at the very end of the loop, IF there was a second message, fully update it here
        await streamedMessage2.edit(content=second_reply_content)
    else: # second message wasn't needed, so make sure to add the last chunks to the first and only message
        await streamedMessage.edit(content=fullMessage)     
    combinedMessage = fullMessage + " " + second_reply_content# full reply content (first message) + second reply content, appended to eachother to keep our history variable in line
    history.append({"role": "assistant", "content": combinedMessage}) # add full message to history, whether there was one or two messages used
    newMessage = 0 # reset new message variable for next time
    #print("got to end of stream function")
    return combinedMessage

#function used for scraping websites, used with the !search command
def get_first_500_words(url, numWords):
    def filter_noise(text):
        # This is a simple example. You can make it as complex as you like!
        noise_phrases = ['Buy Now', 'Advertisement', 'Sponsored', 'Copyright', 'All Rights Reserved']
        for phrase in noise_phrases:
            if phrase in text:
                return False
        return True

    # Set up logging mechanism
    #logging.basicConfig(filename='scraping.log', level=logging.ERROR)

    try:
        #gpt4's cleaner attempt at scraping
        # Set User-Agent and timeout
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        # Create BeautifulSoup object
        soup = BeautifulSoup(response.text, 'html.parser')

        # Step 1: Initial Scrubbing
        tags_to_scrape = ['p', 'h1', 'h2', 'h3']

        scraped_text = []

        for tag in tags_to_scrape:
            elements = soup.find_all(tag)
            for element in elements:
                scraped_text.append(element.text)
        
        # Step 2: Filter out noise
        filtered_text = [text for text in scraped_text if filter_noise(text)]

        # Convert to single string and split into words
        all_filtered_words = ' '.join(filtered_text).split()

        # Step 3: Word Count (limiting to 'numWords')
        first_n_words = all_filtered_words[:numWords]
        
        return ' '.join(first_n_words)
        
    except requests.exceptions.RequestException as e:
        # Log the error and include the URL that caused the error
        #logging.error(f"Error while scraping URL {url}: {str(e)}")
        return (f"Sorry, scraping {url} errored out.")

#summarize a single url
async def summarize(url,channel):
    print("Scraping...")
    scrapedSummaryUrl = get_first_500_words(url,50000)
    try:
        await stream_openai_multi(f"{summarizeArticle} {scrapedSummaryUrl}",history,channel) 
        print("Summarizing...")   
    except Exception as e:
        error_message = str(e)
        print(e)
        await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}",channel)
        return
    return

# defacto googler    
async def silentMultiGoogle(search1, search2, search3, question, channel):
    #turn search terms into an array for easy looping
    searches = [search1, search2, search3]
    #google search1
    # program in api switcher here

    service = build("customsearch", "v1", developerKey=googleApiKey)
    scrapeMessage = await botFunctions.tealMessage("Researching...🔍🌎📄",channel)
    urlList = []
    for item in searches:
        result = service.cse().list(
            q=item,
            cx=googleEngineID
        ).execute()
        print(f"Processing URLs... for {item}")
        # for each search term, pull the top two google searches, for a total of 6 websites total, reviewed
        try:
            url1 = result['items'][0]['link']
            url2 = result['items'][1]['link']
            #url3 = result['items'][2]['link']
        except (TypeError, KeyError):
            print("No URLs found, try rewording your search.")
            await botFunctions.redMessage("No URLs found.",channel)
            return
    
        print("Scraping...")
        #scrape these results with beautiful soup.. mmmm
        scraped1 = get_first_500_words(url1,4000)
        scraped2 = get_first_500_words(url2,4000)
        #scraped3 = get_first_500_words(url3,500)
        #put them all in one variable
        allScraped = (f"\n\n\nURL:{url1}\n -- {scraped1}" or "") + " " + (f"\n\n\nURL:{url2}\n -- {scraped2}" or "")# + " " + (f"\n\n\nURL:{url3}\n -- {scraped3} or ")
        #prepare results for bot
        user_search_obj = {"role": "user", "content": allScraped}
        #we save it to a variable and feed it back to the bot to give us the search results in a more natural manner
        history.append(user_search_obj)
        #clear var for next time
        allScraped = ""
        urlList.append([url1,url2])
        
    await scrapeMessage.delete() # delete the magnifying glass message
    print (str(urlList))
    await botFunctions.tealMessage("Researched.   🔍🌎📄",channel) # research is done, keep this here so we know a search happened
    try:
        botReply = await stream_openai_multi(f"You now have a wealth of information on the topic of my question: ```{question}```. Given the information you have, please answer the question using markdown fomat for readability. DO use emojis. Provide the URL of the most relevant website you used at the bottom.",history, channel)
        return(botReply)
    except Exception as e:
        error_message = str(e)
        print(e)
        await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}",channel)
        return

#resets conversation history back to just identity and date -- to save on tokens when user says !thanks
def resetConvoHistory():
    global history, totalCost, totalTokens, identity
    history = []
    setSystemPrompt()
    print(f"History reset.\n\n")
    totalCost = 0
    totalTokens = 0
    return

#used to see if my comfyui computer is up and running
def is_port_listening(ip_address, port):
    try:
        s = socket.create_connection((ip_address, port), timeout=1)
        s.close()
        return True
    except ConnectionRefusedError:
        return False
    except socket.timeout:
        return False

#function to create and return a prompt for use with comfy
#also used by main image generating tool
async def promptCreation(prompt,channel):
    try:
        discordResponse = await ask_openai(f"""*{prompt}* is the request for an image. Please 
            describe this as if you were describing it to an artist. In your own words, 
            separating your ideas by commas instead of describing them conversationally, 
            describe the art piece. Start with the main subject(s), any actions that may 
            be happening, describe where the image takes place including foreground and 
            background, and end with the style of the image. Do not use proper sentences, 
            just your describing words separated by commas. 
            Event if the prompt is asking for multiple pictures, just describe one of them. 
            Remember, don't use sentences, break your thoughts up by commas and that's it. 
            do NOT use emojis""",history)
        return(discordResponse)
    except Exception as e:
        error_message = str(e)
        print(e)
        await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}",channel)
        return

# set wheatleys mode to Local LLM, 3.5 or 4
async def setModeLLM():
    global aiclient, identity
    aiclient = OpenAI(base_url=f"http://{comfyIP}:{comfyPort}/v1", api_key="lm-studio")
    global model_max_tokens
    model_max_tokens = 16000
    global model
    model = lmStudioModel
    print(f"Model set to {lmStudioModel}")

async def setmodeMini():
    global aiclient, identity
    aiclient = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    global model_max_tokens
    model_max_tokens = 4096
    global model
    model = "gpt-4.1-nano"
    print(f"Model set to gpt-4.1-nano")

async def setModeGPT4():
    global aiclient, identity
    global aiclient
    aiclient = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    global model_max_tokens
    model_max_tokens = 16000
    global model
    model = "gpt-4.1"
    print(f"Model set to gpt-4.1")

async def setModeGroq():
    global aiclient, identity
    aiclient = Groq(api_key=groqApiKey)
    global model_max_tokens
    model_max_tokens = 8192
    global model
    model = groqModel
    print(f"Model set to {groqModel}")

async def setFormerModel(formerModel):
    if (formerModel == "gpt-4.1-nano"):
        await setmodeMini()
        return   
    elif (formerModel == lmStudioModel):
        if is_port_listening(lmstudioIP,lmstudioPort) == True:
            await setModeLLM()
        else: #lm studio isn't running
            await botFunctions.tealMessage(f"{lmStudioModel} is not online.. Sticking with {model}.",channel)
        return
    elif (formerModel == "gpt-4.1"):
        await setModeGPT4()
        return
    elif (formerModel == groqModel):
        await setModeGroq()
        return

# function that runs as soon as bot comes online in Discord
@client.event
async def on_ready():
    global askingAboutHabits, user_habit_data
    global modelTemp
    global fullDate
    global w
    global h
    global notifications
    #change this to the channel id where you want reminders to pop up
    main_channel_id = int(os.environ['mainChannelID'])
    main_channel_id_object = await client.fetch_channel(main_channel_id)
        
    # Setting up database
    # ensure database tables are created
    database.create_habits_table() # not used yet
        
    #banner at the top of the terminal after script is run
    print("\x1b[36mWheatley\x1b[0m is now online in Discord.")
    print('Logged in as {0.user}'.format(client))
    print('Setting Date and identity.')
    setSystemPrompt()
    
    #greeting!
    await botFunctions.tealMessage(f"""👋Good day!\n💬Feel free to start chatting!\n🙏Done with the conversation? Just say 'thanks' somewhere in your message.\n\n
        🔎Need current info? Say the words 'search' and 'please' somewhere in your message.\n🖼️Want a picture or four? Mention the word 'picture' and 'generate' 
        and describe what you'd like to see, as well as how many.\n\n📲If you want to see more commands, just type !help\n\n
        ✅Get reminded and encouraged to do your habits by using !addhabit and !myhabits to check status/streaks (restart bot after adding habit)
        🤖AI Models Available: \n!mini - GPT-4.1-nano\n!gpt4 - GPT-4.1\n!llm - {lmStudioModel}\n!groq - llama 3 70B""",main_channel_id_object)
    if is_port_listening(lmstudioIP,lmstudioPort) == True:
        await botFunctions.blackMessage(f"🟢 Local model {lmStudioModel} is currently online.", main_channel_id_object)
    else:
        await botFunctions.blackMessage(f"🔴 Local model {lmStudioModel} is currently offline.", main_channel_id_object)
    if is_port_listening(comfyIP,comfyPort) == True:
        await botFunctions.blackMessage(f"🟢 Image generation is currently online.", main_channel_id_object)
    else:
        await botFunctions.blackMessage(f"🔴 Image generation is currently offline.", main_channel_id_object)
        
    # OPTIONAL NOTIFICATIONS
    async def remind_exercises():
        channel = await client.fetch_channel(main_channel_id)
        await botFunctions.purpleMessage("🏋️‍♀️ It is imperative that you perform the following exercises as part of your physio regimen:\n- 🧱 Wall stretch: 20 reps in total\n- 🪑 Chair push-ups: 20 reps in total\n- 💪 15 rows with 10 tricep extensions per arm\n- 🙆‍♂️ 20 shrugs\n- 🔙 Corner stretch",channel)
    
    async def daily_weather():
        global modelTemp
        global model
        global history
        resetConvoHistory()
        channel = await client.fetch_channel(main_channel_id)
        # formerModel = model
        # if is_port_listening(lmstudioIP,lmstudioPort) == True:
        #     await setModeLLM()
        positiveMessage = await ask_openai(f"It's the morning, Please say something nice to get my day started off on the right",history)                
        await botFunctions.purpleMessage(positiveMessage,channel)
        resetConvoHistory()
        question = f"Find me an uplifting news story from anywhere. Keep them kind of current, the date is {fullDate} Title it, summarize it three sentences max, leave a URL of where you found it, then leave me with a positive comment of it to start my day."
        searchTerms = await ask_openai(f"Come up with 3 different web searches that you think would help you answer this question :```{question}``` Reply with ONLY the search terms, prepended by 1., 2. then 3. Do not use emojis or explain them.",history)
        # let gpt4 make the terms, and the llm will respond to data
        searchTerms = searchTerms.replace('"', '')
        #split the search terms into three separate variables
        splitSearch=searchTerms.split("\n")
        search1=splitSearch[0]
        search2=splitSearch[1]
        search3=splitSearch[2]
        await silentMultiGoogle(search1, search2, search3, question, channel)
        calculateCost()
        await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ", channel)      
               
        newsPicPrompt = await ask_openai("You just told me some uplifting news, now describe a scene that describes one of the stories you told me. Reply with ONLY the description and nothing more",history)
        if is_port_listening(comfyIP,comfyPort) == True:
            await botFunctions.comfyRefined(newsPicPrompt,1,channel,w,h)
        resetConvoHistory()
        #reset model back to whatever the userleft it at
        # await setFormerModel(formerModel)

    async def gratitudes():
        #asks for your gratitudes daily
        resetConvoHistory()
        channel = await client.fetch_channel(main_channel_id)
        await botFunctions.purpleMessage("🌸What are your three gratitudes for the day?🌿",channel)
        gratitudes = {"role": "user", "content": f"You just asked ```What are your three gratitudes for the day?```. I am just about to tell you what mine are. Give me some reassuring message about my three options but keep your response to a single sentence."}
        history.append(gratitudes)
        await asyncio.sleep(14400)

    # autocreate cronjobs on start
    async def habitReminders(user_id,habit_name):
        global askingAboutHabits
        #asks for your gratitudes daily
        channel = await client.fetch_channel(main_channel_id)

        # *** Dynamically get the streak from the database ***
        # Retrieve the updated habit info
        habit_data = database.get_habit(user_id, habit_name)
        current_streak = habit_data[1]

        #ask the bot to remind you of your habit
        habitMessage = await ask_openai(f"""The user would like you to ask them if they did their habit {habit_name}.
                                  Please remind the user, keeping in mind their current streak of {current_streak} days, to do their habit.
                                  This will help incentivise them, they wouldn't want to lose their streak.                 
                                   """,history)
        await botFunctions.purpleMessage(f"{habitMessage}",channel)
        #flag to ensure you capture users next message to then decide what type of database action to take
        askingAboutHabits = 1
        user_habit_data[user_id] = (habit_name, current_streak)

    # Start the scheduler
    if notifications == 1:
        scheduler.start()
        # scheduler.add_job(remind_exercises, 'cron', hour=19, minute=0, timezone=time_zone)
        # scheduler.add_job(daily_weather, 'cron', hour=7, minute=45, timezone=time_zone)
        # scheduler.add_job(gratitudes, 'cron', hour=21, minute=30, timezone=time_zone)
        
        # New code for dynamic habit reminders
        habits = database.get_all_habits_with_times()
        #print(habits)
        for habit in habits:
            user_id, habit_name, reminder_time, streak = habit
            try:
                hour = int(reminder_time[:2])
                minute = int(reminder_time[2:])
                print(f"Adding habit: {habit_name} for {user_id} at {hour}:{minute}")
                scheduler.add_job(habitReminders, 'cron', hour=hour, minute=minute, args=[user_id, habit_name], timezone=time_zone)
            except Exception as e:
                print(f"Error scheduling reminder for {habit_name}: {e}")
# function that runs on event, so whenever you send something to the bot
@client.event
async def on_message(message):
    global identity, history, totalCost, totalTokens, inputContent, outputFile, image, modelTemp, w, h, searchFlag, askingAboutHabits, user_habit_data
    user_id = str(message.author.id)
     # ignore messages sent by the bot itself to avoid infinite loops
    if message.author == client.user:
        return
    # 3 options here, if they said search, picture, or none of the above
    elif askingAboutHabits == 1 :
        habit_name, streak = user_habit_data[user_id]
        habitYesNo = await ask_openai(f"The user just said {message.content}. Does it sound like they did their habit/task? Reply with a single word, 'yes' or 'no' only.",history)
        if "yes" in str.lower(habitYesNo):
            await stream_openai_multi(f"Respond in a positive manner, the user DID do their habit/task for the day, which was {habit_name} and their streak is now {streak+1}!", history, message.channel)
            database.mark_habit_completed(user_id, habit_name)
        else:
            await stream_openai_multi(f"Respond in an encouraging manner, the user did NOT do their habit/task for the day, which was {habit_name}. They just lost their streak of {streak}.!", history, message.channel)
            #await botFunctions.tealMessage(f"{habitNo}",message.channel)
            database.reset_habit_streak(user_id, habit_name)
        askingAboutHabits = 0
        return
    elif "search" in str.lower(message.content) and "please" in str.lower(message.content) :
        print("search keyword said, forcing search")
        # we're going to flip to llm here, and back again afterward
        formerModel = model
        channel = message.channel
        question = message.content
        streamedMessage = await channel.send("🔎")
        try:
            searchTerms = await ask_openai(f"Come up with 3 different web searches that you think would help you answer this question :```{question}``` Reply with ONLY the search terms, prepended by 1., 2. then 3. Do not use emojis or explain them.",history)
            # let gpt4 make the terms, and the llm will respond to data
            await streamedMessage.delete()
            #strip quotes
            searchTerms = searchTerms.replace('"', '')
            #split the search terms into three separate variables
            splitSearch=searchTerms.split("\n")
            search1=splitSearch[0]
            search2=splitSearch[1]
            search3=splitSearch[2]
            await silentMultiGoogle(search1, search2, search3, question, channel)
            calculateCost()
            await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
            
            
        except Exception as e:
            error_message = str(e)
            print(e)            
            await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}",channel)
            await setFormerModel(formerModel)
    # Picture explicitly requested
    elif any(word in str.lower(message.content) for word in ["picture", "image"]) and "generate" in str.lower(message.content):
    #elif "picture" or "image" in str.lower(message.content) and "generate" in str.lower(message.content):
        print("picture keyword said, generate picture(s)")
        formerModel = model
        channel = message.channel
        if formerModel == lmStudioModel:
            await setmodeMini() #create the prompt with gpt3.5 to not hog ram
        numImages = await ask_openai(f"The user just asked for a picture: {message.content} \n How many pictures does it sound like they wanted? Answer with only the number, like 1, 2, 3 or 4", history)
        print(f"Number of Images: {numImages}")
        if "1" in numImages:
            numImages = 1
        elif "2" in numImages:
            numImages = 2
        elif "3" in numImages:
            numImages = 3
        elif "4" in numImages:
            numImages = 4
        else:
            numImages = 4
        if is_port_listening(comfyIP,comfyPort) == True:
            await botFunctions.yellowMessage(f"Painting {numImages} {w}x{h} image(s)... 🖌🎨\nPlease wait for all of them⌛\n(about 12 seconds per picture⏲️)",channel)
            for i in range(1, numImages + 1):
                #basis = await ask_openai("Describe this image in detail as instructed previously.", history)
                promptForImagine = await promptCreation(message.content,channel)
                print(f"\n\nPrompt {i} - {promptForImagine}")
                try:
                    # Set a timeout for each image loading
                    await asyncio.wait_for(botFunctions.comfyRefined(promptForImagine, 1, channel, w, h), timeout=120)  # e.g., 120 seconds
                except asyncio.TimeoutError:
                    await channel.send(f"Timed out while generating image {i}. Please try again later.")  # Handle the timeout scenario
                except Exception as e:
                    await channel.send(f"An error occurred: {e}")
            calculateCost()
            await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
        else:
            await botFunctions.tealMessage("Sorry, my image generator isn't currently online.",channel)
        await setFormerModel(formerModel)
        return
    #database functions, not working yet  
    elif message.content.startswith("!addhabit"):
        parts = message.content.split(" ")
        if len(parts) >= 3:
            habit_name = parts[1]
            reminder_time = parts[2]
            user_id = str(message.author.id)
            database.create_habit(user_id, habit_name, reminder_time)
            await botFunctions.tealMessage(f"Habit '{habit_name}' added!", message.channel)
        else:
            await botFunctions.redMessage("Please use the format: !addhabit [all one word, eg floss_teeth] [Reminder time in 24hr format eg 0945]", message.channel)
    elif message.content.startswith("!myhabits"):
        user_id = str(message.author.id)
        habits = database.get_habits(user_id)
        if habits:
            message_text = "# Current habit stats:\n"
            for habit in habits:
                message_text += f"## {habit[0]}  :  Streak: {habit[1]}\nLast Completed: {habit[2]}, Reminder: {habit[3]}\n"
            await botFunctions.tealMessage(message_text, message.channel)
        else:
            await botFunctions.redMessage("You have no habits yet!", message.channel)           
    #resets conversation history -- should be needed as saying 'thanks' to the bot resets it too  
    elif '!reset' in message.content:
        member=message.guild.me
        #clear chat history except for starting prompt
        resetConvoHistory()
        await botFunctions.blueMessage("Conversation History Cleared.",message.channel)
        calculateCost()
        await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
        return
    elif "thank" in str.lower(message.content) and len(message.content.split()) < 10: 
            print("User said thanks. Resetting convo.")
            resetConvoHistory()
            await stream_openai_multi(message.content,history,message.channel)
            calculateCost()
            await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
            return

    # set the x and y resolution of comfy images
    elif "!rez" in message.content:
        _, resolution = message.content[2:].split()
        w, h = map(int, resolution.split('x'))
        await botFunctions.yellowMessage(f"Image generation resolution set to {w}x{h}.",message.channel)
        return

    #summarize article OR now Youtube transcript
    elif message.content.startswith('http') or message.content.startswith('www'):
        resetConvoHistory()
        formerModel = model
        vidID = ""        
        try:
            if 'youtube.com' in message.content:
                try:
                    vidID = message.content.split('=')[1]
                    print(f"Video ID: {vidID}")
                    transcript = YouTubeTranscriptApi.get_transcript(vidID, languages=['en', 'en-US'])
                except Exception as e:
                    error_message = str(e)
                    print(e)
                    await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}", message.channel)
                    return
                justText = ' '.join(line['text'] for line in transcript)
                await stream_openai_multi(f"{summarizeInstructions}\n\n{justText}", history, message.channel)                              
                calculateCost()
                await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
                await setFormerModel(formerModel)
                return
                
            elif 'youtu.be' in message.content:
                try:
                    vidID = message.content.split('be/')[1]
                    print(f"Video ID: {vidID}")
                    transcript = YouTubeTranscriptApi.get_transcript(vidID, languages=['en', 'en-US'])
                except Exception as e:
                    error_message = str(e)
                    print(e)
                    await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}", message.channel)
                    return
                justText = ' '.join(line['text'] for line in transcript)
                await stream_openai_multi(f"{summarizeInstructions} \n\n {justText}", history, message.channel)   
                calculateCost()
                await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
                await setFormerModel(formerModel)
                return
            else :
                url = message.content
                await summarize(url, message.channel)            
                calculateCost()
                await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
                #no longer wiping history afterward, this way you can talk to the article and ask follow up questions
                #resetConvoHistory()  # Wiping history for efficiency
                await setFormerModel(formerModel)
                return
        except Exception as e:
            error_message = str(e)
            print(e)            
            await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}", message.channel)
            return
    
    #bot ignores what's entered completely
    elif '!ignore' in message.content:
        print("Ignoring input.")
        return
    
    #processes upscale 4x of attached image if you also say !upscale
    elif len(message.attachments) == 1 and '!upscale' in message.content:
        inputFile = message.attachments[0]
        if is_port_listening(comfyIP,comfyPort) == True:
            await botFunctions.yellowMessage(f"Upscaling attached image 4x🖌🎨\n",message.channel) 
            for attachment in message.attachments:
                # save image locally to server
                with open("ComfyImages/imgToProcess.jpg", "wb") as f:
                    f.write(await attachment.read())
                
                # Open the image using PIL
                pilimage = Image.open('ComfyImages/imgToProcess.jpg')
                if pilimage.mode == 'RGBA':
                    # Convert it to RGB
                    pilimage = pilimage.convert('RGB')
                pic = pilimage

                # Convert PIL Image to base64
                image_io = BytesIO()
                pic.save(image_io, format='JPEG')
                image_base64 = base64.b64encode(image_io.getvalue()).decode('utf-8')

                # Now pass this base64 string to your function
                await botFunctions.comfyUpscale(image_base64,message.channel)
        else:
            return
        return 

    #read attached file and respond with a file as well
    elif len(message.attachments) == 1:
        #get the attached file and read it
        inputFile = message.attachments[0]
        print("Reading File")
        if inputFile.filename.endswith('.txt'):
            print("Processing File...")
            inputContent = await inputFile.read()
            inputContent = inputContent.decode('utf-8')
            #so inputContent is the message to be openai-ified
            try:
                bot_message = await message.channel.send("📑")
                discordResponse = await ask_openai(inputContent,history)
                await bot_message.delete()
                with open(outputFile, "w") as responseFile:
                    responseFile.write(discordResponse)
                await message.channel.send(file=discord.File(outputFile))
                await botFunctions.blackMessage("Please see my response in the attached file.",message.channel)
                calculateCost()
                await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
            except Exception as e:
                error_message = str(e)
                print(e)
                await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}",message.channel)
            return
    
    elif '!braintrust' in message.content:
        try:
            #craft a prompt to have wheatley provide a braintrust of advisors given the question asked
            braintrustRequest=f"""
                You have just been asked {message.content[11:]}. 
                Based on that question, come up with 4 characters that would have helpful insight to share regarding this exact topic.
                Name the Characters and put only their profession before their response, like 'Rick - Car Enthusiast:'.

                For an example of the output I'm looking for, if the question was:
                "is it legal to dig a tunnel to my neighbours backyard?"
                You would answer the users question in the way that each character would answer it, prepending the answer with the name and profession/skill
                example:
                Leon - Lawyer: no, that would be trespassing. I'd advise against it.
                Jared - Landscaper: not only that, it would be unsafe, you'd need the proper tools and bracing if you were to do this
                Amie - Criminal: yea don't do it, I tried to break out of jail once this way and got trapped for 36hrs before someone saved me
                Joe - Your Dad: what are you thinking? I raised you better than this!
                Put yourself in their shoes and try really hard to come up with unique insights given their specific set of skills and experiences.
                Do NOT introduce yourself OR them formally, just show their names, professions and responses.
                Give me a TL;DR of what your thoughts are at the bottom.
                """
            await stream_openai_multi(braintrustRequest,history,message.channel)
            calculateCost()
            await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
        except Exception as e:
            error_message = str(e)
            print(e)        
            await botFunctions.redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}",message.channel)
        return
    elif '!nano' in message.content:
        await botFunctions.tealMessage("gpt-4.1-nano - Activated",message.channel)
        await setmodeMini()
        return
    elif '!gpt4' in message.content:
        await botFunctions.tealMessage("gpt-4.1 - Activated",message.channel)
        await setModeGPT4()
        return
    elif '!groq' in message.content:
        await botFunctions.tealMessage("groq - Activated",message.channel)
        await setModeGroq()
        return
    elif '!llm' in message.content:
        if is_port_listening(lmstudioIP,lmstudioPort) == True:
            await setModeLLM()
            await botFunctions.tealMessage(f"{lmStudioModel} - Activated",message.channel)
        else: #lm studio isn't running
            await botFunctions.tealMessage(f"{lmStudioModel} is not online. Sticking with {model}.",message.channel)
        return
        
    # displays all commands
    elif '!help' in message.content:
        await botFunctions.tealMessage("👋Good day!\n💬Feel free to start chatting!\n🙏Done with the conversation? Just say 'thanks' somewhere in your message.\n\n🔎Need current info? Say the words 'search' and 'please' somewhere in your message.\n🖼️Want a picture or four? Mention the word 'picture' and 'generate' and describe what you'd like to see, as well as how many.\n\n📲If you want to see more commands, just type !help\n",message.channel)
        await botFunctions.blueMessage(f"🤖AI Models Available: \n!mini - GPT-4o-mini\n!gpt4 - GPT-4o\n!llm - {lmStudioModel}\n!groq - llama 3 70B", message.channel )
        if is_port_listening(lmstudioIP,lmstudioPort) == True:
            await botFunctions.blackMessage(f"🟢 Local model {lmStudioModel} is currently online.", message.channel)
        else:
            await botFunctions.blackMessage(f"🔴 Local model {lmStudioModel} is currently offline.", message.channel)
        if is_port_listening(comfyIP,comfyPort) == True:
            await botFunctions.blackMessage(f"🟢 Image generation is currently online.", message.channel)
        else:
            await botFunctions.blackMessage(f"🔴 Image generation is currently offline.", message.channel)
        await botFunctions.blackMessage(f"""The following functions are currently available:\n
            Simply send a message and press enter and wait for a response. No need to @ the bot, or start a thread or anything.\n
            There are many commands as well:\n""", message.channel)
        await botFunctions.blackMessage(f"""**Summarize an article or youtube video:**\n
            Simply paste the youtube or article url into chat and hit enter. In the case of youtube it will pull the transcript and summarize it. You can then talk to the results by using the !16k flag to ensure you have the tokens to do so\n
            **!addhabit** - Add a habit reminder, keeps track of streaks and encourages you! (restart bot after adding habit)\n
            **!myhabits** - lists current habits\n
            **!braintrust** - dynamically makes  bunch of 'professional' identity's to answer your question\n
            **!ignore** - the bot won't react at all, so just in case you want to save yourself a message for later or something\n
            **!upscale AND attach an image. the image will be upscaled x4 on all dimensions and sent back
            **File management:**\n
            There is no command here, just drop a text file in as an attachment, include a prompt within that file. The bot will respond within an attachment that it sends back to you.\n
            In this manner you can get around the 2000 word limit of discord. Especially useful when you want a massive prompt/response from GPT4.\n
            """,message.channel)
        return
    # no search or picture wanted, streaming, default chat call:
    else:
        await stream_openai_multi(message.content,history,message.channel)
        calculateCost()
        await botFunctions.tealMessage(f"{model} 🎟️ Tokens {totalTokens} ",message.channel)
        return  
    
#intent, in case I want to revisit:
#Streaming by default - with intent
#     try:            
#         if (model != "Gemini" and model != "open-mixtral-8x7b"): #took out local to test    model != "Local LLM" and 
#             #add user message to history so that main memory has access to it
#             #history.append(user_response_obj)
#             #ask the non-history keeping openai to discern intent
#             intent = await ask_openai_intent(f"""
#                 Given the user's recent input '{message.content}', please discern the intent of this message based on the following guidelines:
#                 1 - Choose 1 by default unless the user is asking for an image or an online search
#                 2 - Choose 2 if the user's message is specifically asking to create an image of some sort.
#                 3 - Only choose this option if the user's message contains clear and explicit requests for an online search using phrases like 'search for', 'look up on the internet', 'find online information about', or 'Google for me'.
                
#                 IMPORTANT: Avoid option 3 unless specifically asked to search. EVEN if you don't know the answer or can't know the answer without a google search.
                
#                 Based on these guidelines, reply with ONLY the digit 1, 2, or 3.
#                 """, history)
#             # intent = await ask_openai_intent(f"""
#             #     Given the users recent input '{message.content}'. Please discern the intent of this message.:
#             #     1 - User is looking for a standard response from you
#             #     2 - User is specifically requesting creation of an image
#             #     3 - User is specifically requesting an online search
#             #     Reply with ONLY the digit 1, 2 or 3.
#             #     """, history)
#             if "1" in intent: #respond normally
#                 await stream_openai_multi(message.content,history,message.channel)
#                 calculateCost()
#                 await tealMessage(f"🎟️ Tokens {totalTokens} -- 🤖 Model {model}",message.channel)
#                 print(f"Convo History\n{history}")
#                 print(f"IntentHistory\n{intentHistory}")
#                 return
#             elif "2" in intent: #generate a pic
#                 channel = message.channel
#                 numImages = await ask_openai_intent("How many pictures does it sound like they wanted? Answer with only the number, and nothing higher than 4.", history)
#                 numImages = int(numImages)
#                 if (numImages > 4):
#                     await channel.send("Sorry that's too many, but I'll make you 4.")
#                     numImages = 4
#                 await yellowMessage(f"Painting {numImages} {w}x{h} images... 🖌🎨\nPlease wait for all of them⌛\n(about 12 seconds per picture⏲️)",channel)
#                 for i in range(1, numImages + 1):
#                     #basis = await ask_openai("Describe this image in detail as instructed previously.", history)
#                     promptForImagine = await promptCreation(message.content,channel)
#                     await comfyRefined(promptForImagine,1,channel,w,h)
#                 # member=message.guild.me
#                 # await member.edit(nick='Wheatley')
#                 calculateCost()
#                 await tealMessage(f"🎟️ Tokens {totalTokens} -- 🤖 Model {model}",message.channel)
#                 print(f"Convo History\n{history}")
#                 print(f"IntentHistory\n{intentHistory}")
#                 return
#             elif "3" in intent: # search
#                 #wipe history as this could get big
#                 # resetConvoHistory()
#                 channel = message.channel
#                 # question = message.content
#                 #print(history[-3:])
#                 question = message.content
#                 streamedMessage = await channel.send("🔎")
#                 try:
#                     searchTerms = await ask_openai(f"Come up with 3 different web searches that you think would help you answer this question :```{question}``` Reply with ONLY the search terms, prepended by 1., 2. then 3. Do not use emojis or explain them.",history)
#                     await streamedMessage.delete()
#                     #strip quotes
#                     searchTerms = searchTerms.replace('"', '')
#                     #await yellowMessage(f"Searching:\n{searchTerms}.",channel)
#                     #split the search terms into three separate variables
#                     splitSearch=searchTerms.split("\n")
#                     search1=splitSearch[0]
#                     search2=splitSearch[1]
#                     search3=splitSearch[2]
#                     await silentMultiGoogle(search1, search2, search3, question, channel)
#                     calculateCost()
#                     await tealMessage(f"🎟️ Tokens {totalTokens} -- 🤖 Model {model}",message.channel)
#                     print(f"Convo History\n{history}")
#                     print(f"IntentHistory\n{intentHistory}")
#                     #search uses so many tokens now, replying would create an error unless you use !16k flag so just to be safe, wiping history by default
#                     #resetConvoHistory() 
#                     return
#                 except Exception as e:
#                     error_message = str(e)
#                     print(e)            
#                     await redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}",channel)
#                     return
#             else:
#                 await blurpleMessage(intent,message.channel)
#                 return
#         elif(model=="Local LLM"):
#             #sends users question to openai
#             await stream_openai_multi(message.content,history,message.channel)
#             calculateCost()
#             await tealMessage(f"🎟️ Tokens {totalTokens} -- 🤖 Model {model}",message.channel)
#         elif(model=="Gemini"):
#             channel = message.channel
#             googleMessage = await ask_gemini(message.content[7:],ghistory)
#             await channel.send(googleMessage)
#             await tealMessage(f"🎟️ Tokens {totalTokens} -- 🤖 Model {model}",message.channel)
#         elif(model=="open-mixtral-8x7b"):
#             await stream_mistral_multi(message.content,history,message.channel)
#             calculateCost()
#             await tealMessage(f"🎟️ Tokens {totalTokens} -- 🤖 Model {model}",message.channel)
#     except Exception as e:
#         error_message = str(e)
#         print(e)        
#         await redMessage(f"Shoot..Something went wrong or timed out.\nHere's the error message:\n{error_message}",message.channel)
#         return

# client.run(discordBotToken)
#---/DISCORD SECTION---#



# fire up the bot
client.run(discordBotToken)