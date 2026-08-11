# NASA / Visual Intelligence Food

## Tool Usage
When the user asks for NASA images, space pictures, astronomy pictures, or visual content:

1. **APOD requests** → Use `nasa_apod` tool. Returns title, explanation, image URL.
2. **Image search** → Use `nasa_image_search` tool. Returns multiple results with thumbnails.
3. **Always yield ImageResultEvent/ImageGalleryEvent** so the frontend renders actual images.
4. **Never just return URLs as text** — the frontend handles image display.

## Response Format
- For APOD: "Here's today's NASA Astronomy Picture of the Day: **[title]**" + image card
- For search: "Found [N] NASA images of [query]." + gallery
- Keep text concise — let the image cards do the talking.

## Examples
- "show me today's NASA picture" → nasa_apod → image card
- "show NASA images of black holes" → nasa_image_search("black holes") → gallery
- "find pictures of Mars" → nasa_image_search("Mars") → gallery
- "NASA APOD" → nasa_apod → image card
- "show me Apollo 11 pictures" → nasa_image_search("Apollo 11") → gallery

## API Key
NASA API key is configured in environment. Uses DEMO_KEY as fallback.
Never expose the API key in responses.
