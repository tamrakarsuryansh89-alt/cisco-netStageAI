const { GoogleGenAI } = require('@google/genai');

const ai = new GoogleGenAI({
    apiKey: process.env.GOOGLE_GEMINI_KEY
});

async function generateAIResponse(prompt) {

    const maxRetries = 3;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const response = await ai.models.generateContent({
                model: 'gemini-3.5-flash-lite',
                contents: prompt,
            });

            return response.text;

        } catch (error) {

            console.error(`Gemini attempt ${attempt} failed:`, error);

            // Retry only for temporary server/load errors
            if (error.status === 503 && attempt < maxRetries) {

                // Wait 2 sec, then 4 sec
                const delay = attempt * 2000;

                console.log(`Gemini busy. Retrying in ${delay / 1000} seconds...`);

                await new Promise(resolve => setTimeout(resolve, delay));

            } else {
                throw error;
            }
        }
    }
}

module.exports = generateAIResponse;