import re

emoteRegex = [
    # Emotes starting with underscores, retrieve group 2
    re.compile(r"^(_{1,2}\*{0,3}([^_*]*)\*{0,3}_{1,2})$"),
    # Emotes starting with asterisks, retrieve group 2
    re.compile(r"^(\*{1}|\*{3})_{0,2}([^_*]*)_{0,2}(\*{1}|\*{3})$")
]

def convertEmote(msgIn):
    if emoteRegex[0].match(msgIn):
        # Emote starts with underscore
        msgOut = '_' + emoteRegex[0].match(msgIn).group(2) + '_'
    elif emoteRegex[1].match(msgIn):
        # Emote starts with asterisk
        msgOut = '_' + emoteRegex[1].match(msgIn).group(2) + '_'
    elif msgIn.startswith('/me '):
        msgOut = '_' + msgIn[4:] + '_'
    else:
        # Ain't no emote
        msgOut = msgIn

    return(msgOut)

def escapeFormatting(msgIn):
    #Escape things like :
    # bold (*), italics (_), spoilers (|), strikethrough (~), quote (>), and code (`)
    msgOut = msgIn.replace('_','\_').replace('*','\*').replace('|','\|').replace('~','\~').replace('>','\>').replace('`','\`')

    return(msgOut)


def mentionToSelfVar(msgIn, botRole, botID):
    msgOut = msgIn

    # Nick ping
    nick = '<@' + str(botID) + '>'
    msgOut = msgOut.replace('!','').replace(nick,'$self') 
    # Role ping
    role = '<@&' + str(botRole) + '>'
    msgOut = msgOut.replace(role,'$self') 

    return(msgOut)

def convertLinkMarkdown(msgIn):
    searchResults = re.findall(r'\[.+?\]',msgIn)
    links = []
    msgOut = msgIn

    if len(searchResults) > 0:
        links = (list(set(searchResults)))
        for i in links:
            msgOut = msgOut.replace(i, i + f"""(https://www.urbandictionary.com/define.php?term={i.strip('[').strip(']').replace(' ','%20')})""" )

    return(msgOut)
    
