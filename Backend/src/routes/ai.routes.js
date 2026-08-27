const express = require('express');
const aiController = require("../controllers/ai.controller")

const router = express.Router();

router.post("/get-review", aiController.getResponse)
router.post("/check", aiController.checkConfig)

module.exports = router;