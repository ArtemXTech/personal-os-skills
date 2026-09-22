# Chief of AI skill

Use one coordinating agent to route bounded tasks to persistent specialist agents, recover status, and verify returned work.

## Install from the marketplace

1. In Claude Code, run:

   ```text
   /plugin marketplace add ArtemXTech/personal-os-skills
   ```

2. Run `/plugin`, open **Discover**, and install **chief-of-ai-skill** for your user account.
3. Restart Claude Code.

For another compatible agent, copy this `chief-of-ai` folder into its skills directory and ask the agent to read `SKILL.md`.

The skill uses the task and conversation tools supplied by your agent harness. It does not install those tools or connect accounts for you.
