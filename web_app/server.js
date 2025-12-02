require('dotenv').config();
const express = require('express');
const { Pool } = require('pg');
const axios = require('axios');
const path = require('path');

const app = express();
const port = 3000;

// 1. Connect to Database ("The Memory")
const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false } // Required for Supabase/Neon
});

// Setup View Engine (EJS)
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static('public'));

// --- ROUTE 1: The Dashboard (Home Page) ---
app.get('/', async (req, res) => {
    try {
        // Fetch upcoming matches from the database
        // We join with teams to get names instead of IDs
        const query = `
            SELECT 
                m.match_id, 
                m.date, 
                t1.name as home_team, 
                t2.name as away_team 
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.team_id
            JOIN teams t2 ON m.away_team_id = t2.team_id
            WHERE m.date >= CURRENT_DATE
            ORDER BY m.date ASC
            LIMIT 10;
        `;

        const result = await pool.query(query);

        // Render the HTML page with this data
        res.render('index', { matches: result.rows });

    } catch (err) {
        console.error("Database Error:", err);
        res.send("Error loading matches. Is the database connected?");
    }
});

// --- ROUTE 2: The "Ask Oracle" Button ---
// When user clicks "Predict", this calls the Python API
app.get('/predict/:matchId', async (req, res) => {
    const { matchId } = req.params;
    console.log(`🔮 Asking Python Brain about match: ${matchId}`);

    try {
        // CALL THE PYTHON MICROSERVICE
        const pythonResponse = await axios.post(`${process.env.PYTHON_API_URL}/predict/match_id?match_id=${matchId}`);

        // Send the answer back to the frontend
        res.json(pythonResponse.data);

    } catch (err) {
        console.error("AI Error:", err.message);
        res.status(500).json({
            error: "The Oracle is sleeping (Python API not running or Match ID invalid)."
        });
    }
});

// Start the Server
app.listen(port, () => {
    console.log(`🚀 Web Interface running at http://localhost:${port}`);
});