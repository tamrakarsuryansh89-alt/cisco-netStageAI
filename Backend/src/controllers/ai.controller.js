const aiService = require('../services/ai.service');
const runRuleChecker = require('../services/ruleChecker.service');

module.exports.getResponse = async (req, res) => {
    try {
        const prompt = req.body.prompt;
        if (!prompt) return res.status(400).send({ error: "Prompt is required" });
        const response = await aiService(prompt);
        res.send(response);
    } catch (error) {
        console.error(error);
        res.status(500).send({ error: "Internal Server Error" });
    }
};

module.exports.checkConfig = async (req, res) => {
    try {
        const { interface_brief, show_run, show_vlan_brief, show_ip_route } = req.body;
        if (!interface_brief && !show_run && !show_vlan_brief && !show_ip_route) {
            return res.status(400).send({ error: "At least one CLI output is required" });
        }
        const result = await runRuleChecker({ interface_brief, show_run, show_vlan_brief, show_ip_route });
        res.send(result);
    } catch (error) {
        console.error(error);
        res.status(500).send({ error: "Internal Server Error" });
    }
};
