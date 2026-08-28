const { GoogleGenAI } = require('@google/genai');

const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_GEMINI_KEY });

async function generateAIResponse(prompt) {
    const response = await ai.models.generateContent({
      model: 'gemini-3.1-flash-lite',
        contents: prompt,
    });
    return response.text;
}

module.exports = generateAIResponse;
