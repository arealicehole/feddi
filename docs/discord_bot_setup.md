# Discord Bot Setup Guide for AccountME

This guide provides detailed instructions for setting up the Discord bot for the AccountME accounting system.

## 1. Register a New Application on Discord Developer Portal

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Log in with your Discord account if you're not already logged in
3. Click the "New Application" button in the top-right corner
4. Enter "AccountME" (or your preferred name) as the application name
5. Accept the Discord Developer Terms of Service and Developer Policy
6. Click "Create"

## 2. Create Bot Account and Generate Token

1. In your new application, click on the "Bot" tab in the left sidebar
2. Click the "Add Bot" button
3. Confirm by clicking "Yes, do it!"
4. Under the "TOKEN" section, click "Reset Token" (you'll need to confirm this action)
5. Copy the token that appears - this is your bot's authentication token
6. **IMPORTANT**: Keep this token secret! Anyone with this token can control your bot
7. In the `.env` file of your project, replace `your_discord_bot_token_here` with your actual token:
   ```
   DISCORD_TOKEN=your_actual_token_here
   ```

## 3. Configure Bot Settings

1. Under the "Bot" tab, configure the following settings:
   - **Username**: Set to "AccountME" or your preferred bot name
   - **Icon**: Upload a custom icon for your bot (optional)
   - **PUBLIC BOT**: Toggle OFF if you don't want others to add your bot to their servers
   - **REQUIRES OAUTH2 CODE GRANT**: Keep this OFF (unless you have specific OAuth2 requirements)
   - **PRESENCE INTENT**: Toggle ON
   - **SERVER MEMBERS INTENT**: Toggle ON
   - **MESSAGE CONTENT INTENT**: Toggle ON (required for reading message content)

2. Click "Save Changes" at the bottom of the page

## 4. Set Required Permissions

The bot needs specific permissions to function properly:

- Read Messages/View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History

These permissions will be configured in the OAuth2 URL generation step.

## 5. Generate OAuth2 URL for Bot Installation

1. Click on the "OAuth2" tab in the left sidebar
2. Select "URL Generator" in the sub-menu
3. Under "SCOPES", check the "bot" option
4. Under "BOT PERMISSIONS", check the following permissions:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
5. The generated URL will appear at the bottom of the page
6. Copy this URL and open it in your web browser
7. Select the server where you want to add the bot
8. Click "Authorize"
9. Complete the CAPTCHA verification if prompted

## 6. Verify Bot Installation

1. Go to your Discord server
2. Verify that the bot appears in the member list (it will initially be offline)
3. Start the bot by running `python bot/main.py` in your project directory
4. The bot should come online in your server
5. Test the bot by sending the command `!ping` in a channel where the bot has access
6. The bot should respond with "Pong!" and the current latency

## 7. Additional Configuration

The bot's presence (status message) is configured in the `main.py` file. By default, it shows "Listening to !help", but you can customize this by modifying the following code:

```python
# Set bot presence
await bot.change_presence(activity=discord.Activity(
    type=discord.ActivityType.listening, 
    name=f"{COMMAND_PREFIX}help"
))
```

Available activity types include:
- `discord.ActivityType.playing` - "Playing [name]"
- `discord.ActivityType.streaming` - "Streaming [name]"
- `discord.ActivityType.listening` - "Listening to [name]"
- `discord.ActivityType.watching` - "Watching [name]"
- `discord.ActivityType.competing` - "Competing in [name]"

## Troubleshooting

### Bot Doesn't Come Online
- Verify that the token in your `.env` file is correct
- Check that you've enabled the necessary intents in the Developer Portal
- Ensure your bot has the required permissions in your server

### Bot Doesn't Respond to Commands
- Check that the bot is online
- Verify that you're using the correct command prefix (default is `!`)
- Ensure the bot has permission to read messages and send messages in the channel
- Check the console output for any error messages

### Permission Issues
- If the bot can't perform certain actions, verify that it has the necessary permissions
- You may need to adjust the bot's role position in your server's role hierarchy