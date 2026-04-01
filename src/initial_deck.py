"""Initial OpenClaw onboarding slide deck."""

INTRO_DECK_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OpenClaw Onboarding</title>
  <style>
    .deck {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2rem;
      padding: 2rem;
      background: #0a0a0a;
      min-height: 100vh;
    }
    .slide {
      width: 960px;
      height: 540px;
      overflow: hidden;
      position: relative;
      background: #0f172a;
      box-shadow: 0 4px 24px rgba(0,0,0,0.4);
      border-radius: 8px;
      flex-shrink: 0;
    }
  </style>
</head>
<body>
  <div class="deck">

    <!-- Slide 1: Title -->
    <section class="slide" style="padding: 60px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
      <h1 style="font-family: Arial, sans-serif; font-size: 64px; font-weight: 700; color: #ffffff; margin: 0;">OpenClaw</h1>
      <p style="font-family: Arial, sans-serif; font-size: 24px; color: #94a3b8; margin: 16px 0 0 0;">Your AI Agent Swarm</p>
      <div style="width: 80px; height: 4px; background: #3b82f6; border-radius: 2px; margin-top: 32px;"></div>
    </section>

    <!-- Slide 2: The Problem -->
    <section class="slide" style="padding: 48px 56px; display: flex; flex-direction: column;">
      <h2 style="font-family: Arial, sans-serif; font-size: 36px; font-weight: 700; color: #ffffff; margin: 0 0 32px 0;">Managing AI Is Hard</h2>
      <div style="display: flex; flex-direction: column; gap: 20px; flex: 1;">
        <div style="display: flex; align-items: flex-start; gap: 16px;">
          <div style="width: 8px; height: 8px; background: #ef4444; border-radius: 50%; margin-top: 10px; flex-shrink: 0;"></div>
          <p style="font-family: Arial, sans-serif; font-size: 20px; color: #e2e8f0; margin: 0;">Dozens of disconnected AI tools that don't talk to each other</p>
        </div>
        <div style="display: flex; align-items: flex-start; gap: 16px;">
          <div style="width: 8px; height: 8px; background: #f59e0b; border-radius: 50%; margin-top: 10px; flex-shrink: 0;"></div>
          <p style="font-family: Arial, sans-serif; font-size: 20px; color: #e2e8f0; margin: 0;">Hours spent on manual setup, prompting, and babysitting</p>
        </div>
        <div style="display: flex; align-items: flex-start; gap: 16px;">
          <div style="width: 8px; height: 8px; background: #f59e0b; border-radius: 50%; margin-top: 10px; flex-shrink: 0;"></div>
          <p style="font-family: Arial, sans-serif; font-size: 20px; color: #e2e8f0; margin: 0;">No way to get agents to coordinate on complex workflows</p>
        </div>
      </div>
      <p style="font-family: Arial, sans-serif; font-size: 14px; color: #475569; margin: 0; margin-top: auto;">You shouldn't need to be an AI engineer to use AI effectively.</p>
    </section>

    <!-- Slide 3: What is OpenClaw -->
    <section class="slide" style="padding: 48px 56px; display: flex; flex-direction: column;">
      <h2 style="font-family: Arial, sans-serif; font-size: 36px; font-weight: 700; color: #ffffff; margin: 0 0 24px 0;">What is OpenClaw?</h2>
      <p style="font-family: Arial, sans-serif; font-size: 22px; color: #cbd5e1; margin: 0 0 32px 0;">We build and host a <span style="color: #3b82f6; font-weight: 600;">swarm of AI agents</span> that work together to handle your workflows.</p>
      <div style="display: flex; gap: 24px; flex: 1; align-items: center;">
        <div style="flex: 1; background: #1e293b; border-radius: 12px; padding: 24px; text-align: center;">
          <p style="font-family: Arial, sans-serif; font-size: 32px; margin: 0 0 8px 0;">1</p>
          <p style="font-family: Arial, sans-serif; font-size: 16px; color: #94a3b8; margin: 0;">Tell us what you need</p>
        </div>
        <p style="font-family: Arial, sans-serif; font-size: 24px; color: #475569; margin: 0;">→</p>
        <div style="flex: 1; background: #1e293b; border-radius: 12px; padding: 24px; text-align: center;">
          <p style="font-family: Arial, sans-serif; font-size: 32px; margin: 0 0 8px 0;">2</p>
          <p style="font-family: Arial, sans-serif; font-size: 16px; color: #94a3b8; margin: 0;">We design your swarm</p>
        </div>
        <p style="font-family: Arial, sans-serif; font-size: 24px; color: #475569; margin: 0;">→</p>
        <div style="flex: 1; background: #1e293b; border-radius: 12px; padding: 24px; text-align: center;">
          <p style="font-family: Arial, sans-serif; font-size: 32px; margin: 0 0 8px 0;">3</p>
          <p style="font-family: Arial, sans-serif; font-size: 16px; color: #94a3b8; margin: 0;">Agents work for you 24/7</p>
        </div>
      </div>
    </section>

    <!-- Slide 4: How It Works -->
    <section class="slide" style="padding: 48px 56px; display: flex; flex-direction: column;">
      <h2 style="font-family: Arial, sans-serif; font-size: 36px; font-weight: 700; color: #ffffff; margin: 0 0 24px 0;">How It Works</h2>
      <div style="display: flex; flex-direction: column; gap: 24px; flex: 1; justify-content: center;">
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="width: 48px; height: 48px; background: #1e40af; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <p style="font-family: Arial, sans-serif; font-size: 20px; font-weight: 700; color: #ffffff; margin: 0;">1</p>
          </div>
          <div>
            <p style="font-family: Arial, sans-serif; font-size: 20px; font-weight: 600; color: #ffffff; margin: 0;">You describe your workflow</p>
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #94a3b8; margin: 4px 0 0 0;">Just talk to us about what you do and what's painful</p>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="width: 48px; height: 48px; background: #1e40af; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <p style="font-family: Arial, sans-serif; font-size: 20px; font-weight: 700; color: #ffffff; margin: 0;">2</p>
          </div>
          <div>
            <p style="font-family: Arial, sans-serif; font-size: 20px; font-weight: 600; color: #ffffff; margin: 0;">We design your agent team</p>
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #94a3b8; margin: 4px 0 0 0;">Each agent has a role, tools, and knows how to collaborate</p>
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 20px;">
          <div style="width: 48px; height: 48px; background: #1e40af; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <p style="font-family: Arial, sans-serif; font-size: 20px; font-weight: 700; color: #ffffff; margin: 0;">3</p>
          </div>
          <div>
            <p style="font-family: Arial, sans-serif; font-size: 20px; font-weight: 600; color: #ffffff; margin: 0;">Deploy and run</p>
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #94a3b8; margin: 4px 0 0 0;">We host everything — your agents run 24/7 with human-in-the-loop checks</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Slide 5: Example - Bug Fixer Agent -->
    <section class="slide" style="padding: 48px 56px; display: flex; flex-direction: column;">
      <p style="font-family: Arial, sans-serif; font-size: 14px; font-weight: 600; color: #3b82f6; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 1px;">Example Agent</p>
      <h2 style="font-family: Arial, sans-serif; font-size: 34px; font-weight: 700; color: #ffffff; margin: 0 0 28px 0;">Bug Fixer</h2>
      <div style="display: flex; gap: 16px; flex: 1; align-items: center;">
        <div style="flex: 1; display: flex; flex-direction: column; gap: 12px;">
          <div style="background: #1e293b; border-radius: 8px; padding: 16px; display: flex; align-items: center; gap: 12px;">
            <div style="width: 32px; height: 32px; background: #7c3aed; border-radius: 6px; flex-shrink: 0;"></div>
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #e2e8f0; margin: 0;">Screenshot posted in Slack</p>
          </div>
          <div style="background: #1e293b; border-radius: 8px; padding: 16px; display: flex; align-items: center; gap: 12px;">
            <div style="width: 32px; height: 32px; background: #059669; border-radius: 6px; flex-shrink: 0;"></div>
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #e2e8f0; margin: 0;">Agent debugs the issue</p>
          </div>
          <div style="background: #1e293b; border-radius: 8px; padding: 16px; display: flex; align-items: center; gap: 12px;">
            <div style="width: 32px; height: 32px; background: #0891b2; border-radius: 6px; flex-shrink: 0;"></div>
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #e2e8f0; margin: 0;">Runs tests to verify</p>
          </div>
          <div style="background: #1e293b; border-radius: 8px; padding: 16px; display: flex; align-items: center; gap: 12px;">
            <div style="width: 32px; height: 32px; background: #dc2626; border-radius: 6px; flex-shrink: 0;"></div>
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #e2e8f0; margin: 0;">Opens a pull request for review</p>
          </div>
        </div>
        <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;">
          <p style="font-family: Arial, sans-serif; font-size: 15px; color: #64748b; margin: 0; text-align: center;">Connects to: Slack, GitHub, test runner</p>
        </div>
      </div>
    </section>

    <!-- Slide 6: Example - Knowledge Base Agent -->
    <section class="slide" style="padding: 48px 56px; display: flex; flex-direction: column;">
      <p style="font-family: Arial, sans-serif; font-size: 14px; font-weight: 600; color: #3b82f6; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 1px;">Example Agent</p>
      <h2 style="font-family: Arial, sans-serif; font-size: 34px; font-weight: 700; color: #ffffff; margin: 0 0 28px 0;">Knowledge Base</h2>
      <div style="display: flex; gap: 32px; flex: 1;">
        <div style="flex: 1; display: flex; flex-direction: column; gap: 16px;">
          <p style="font-family: Arial, sans-serif; font-size: 18px; font-weight: 600; color: #e2e8f0; margin: 0;">Ingests from everywhere</p>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            <div style="background: #1e293b; border-radius: 6px; padding: 8px 16px;">
              <p style="font-family: Arial, sans-serif; font-size: 14px; color: #94a3b8; margin: 0;">Twitter</p>
            </div>
            <div style="background: #1e293b; border-radius: 6px; padding: 8px 16px;">
              <p style="font-family: Arial, sans-serif; font-size: 14px; color: #94a3b8; margin: 0;">Bookmarks</p>
            </div>
            <div style="background: #1e293b; border-radius: 6px; padding: 8px 16px;">
              <p style="font-family: Arial, sans-serif; font-size: 14px; color: #94a3b8; margin: 0;">Papers</p>
            </div>
            <div style="background: #1e293b; border-radius: 6px; padding: 8px 16px;">
              <p style="font-family: Arial, sans-serif; font-size: 14px; color: #94a3b8; margin: 0;">Docs</p>
            </div>
            <div style="background: #1e293b; border-radius: 6px; padding: 8px 16px;">
              <p style="font-family: Arial, sans-serif; font-size: 14px; color: #94a3b8; margin: 0;">Notes</p>
            </div>
          </div>
        </div>
        <div style="flex: 1; display: flex; flex-direction: column; gap: 16px;">
          <p style="font-family: Arial, sans-serif; font-size: 18px; font-weight: 600; color: #e2e8f0; margin: 0;">Query anytime</p>
          <div style="background: #1e293b; border-radius: 12px; padding: 20px;">
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #64748b; margin: 0 0 8px 0; font-style: italic;">"What did I read about transformer architectures last week?"</p>
            <p style="font-family: Arial, sans-serif; font-size: 15px; color: #e2e8f0; margin: 0;">Returns relevant content with sources and context.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Slide 7: Example - Personal CRM Agent -->
    <section class="slide" style="padding: 48px 56px; display: flex; flex-direction: column;">
      <p style="font-family: Arial, sans-serif; font-size: 14px; font-weight: 600; color: #3b82f6; margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 1px;">Example Agent</p>
      <h2 style="font-family: Arial, sans-serif; font-size: 34px; font-weight: 700; color: #ffffff; margin: 0 0 28px 0;">Personal CRM</h2>
      <div style="display: flex; gap: 32px; flex: 1; align-items: center;">
        <div style="flex: 1; display: flex; flex-direction: column; gap: 16px;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 10px; height: 10px; background: #3b82f6; border-radius: 50%; flex-shrink: 0;"></div>
            <p style="font-family: Arial, sans-serif; font-size: 18px; color: #e2e8f0; margin: 0;">Syncs contacts from LinkedIn, WhatsApp, email</p>
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 10px; height: 10px; background: #3b82f6; border-radius: 50%; flex-shrink: 0;"></div>
            <p style="font-family: Arial, sans-serif; font-size: 18px; color: #e2e8f0; margin: 0;">Tracks relationship history</p>
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 10px; height: 10px; background: #3b82f6; border-radius: 50%; flex-shrink: 0;"></div>
            <p style="font-family: Arial, sans-serif; font-size: 18px; color: #e2e8f0; margin: 0;">Drafts personalized messages</p>
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 10px; height: 10px; background: #3b82f6; border-radius: 50%; flex-shrink: 0;"></div>
            <p style="font-family: Arial, sans-serif; font-size: 18px; color: #e2e8f0; margin: 0;">Reminds you to follow up</p>
          </div>
        </div>
        <div style="flex: 1; background: #1e293b; border-radius: 12px; padding: 24px;">
          <p style="font-family: Arial, sans-serif; font-size: 14px; color: #64748b; margin: 0 0 12px 0;">You approve before anything sends</p>
          <p style="font-family: Arial, sans-serif; font-size: 16px; color: #e2e8f0; margin: 0;">Human-in-the-loop: the agent drafts, you decide.</p>
        </div>
      </div>
    </section>

    <!-- Slide 8: The Swarm -->
    <section class="slide" style="padding: 48px 56px; display: flex; flex-direction: column;">
      <h2 style="font-family: Arial, sans-serif; font-size: 36px; font-weight: 700; color: #ffffff; margin: 0 0 24px 0;">The Swarm</h2>
      <p style="font-family: Arial, sans-serif; font-size: 20px; color: #cbd5e1; margin: 0 0 28px 0;">Your agents don't work in isolation — they collaborate.</p>
      <div style="display: flex; gap: 16px; flex: 1; align-items: center; justify-content: center;">
        <div style="background: #1e293b; border: 2px solid #1e40af; border-radius: 12px; padding: 20px; width: 160px; text-align: center;">
          <p style="font-family: Arial, sans-serif; font-size: 16px; font-weight: 600; color: #ffffff; margin: 0;">Agent A</p>
          <p style="font-family: Arial, sans-serif; font-size: 13px; color: #94a3b8; margin: 4px 0 0 0;">Monitors</p>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px; align-items: center;">
          <p style="font-family: Arial, sans-serif; font-size: 20px; color: #3b82f6; margin: 0;">→</p>
          <p style="font-family: Arial, sans-serif; font-size: 11px; color: #475569; margin: 0;">triggers</p>
          <p style="font-family: Arial, sans-serif; font-size: 20px; color: #3b82f6; margin: 0;">←</p>
        </div>
        <div style="background: #1e293b; border: 2px solid #059669; border-radius: 12px; padding: 20px; width: 160px; text-align: center;">
          <p style="font-family: Arial, sans-serif; font-size: 16px; font-weight: 600; color: #ffffff; margin: 0;">Agent B</p>
          <p style="font-family: Arial, sans-serif; font-size: 13px; color: #94a3b8; margin: 4px 0 0 0;">Executes</p>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px; align-items: center;">
          <p style="font-family: Arial, sans-serif; font-size: 20px; color: #3b82f6; margin: 0;">→</p>
          <p style="font-family: Arial, sans-serif; font-size: 11px; color: #475569; margin: 0;">reports</p>
          <p style="font-family: Arial, sans-serif; font-size: 20px; color: #3b82f6; margin: 0;">←</p>
        </div>
        <div style="background: #1e293b; border: 2px solid #7c3aed; border-radius: 12px; padding: 20px; width: 160px; text-align: center;">
          <p style="font-family: Arial, sans-serif; font-size: 16px; font-weight: 600; color: #ffffff; margin: 0;">Agent C</p>
          <p style="font-family: Arial, sans-serif; font-size: 13px; color: #94a3b8; margin: 4px 0 0 0;">Reports</p>
        </div>
      </div>
      <p style="font-family: Arial, sans-serif; font-size: 14px; color: #475569; margin: 16px 0 0 0; text-align: center;">Shared context, coordinated handoffs, unified logging</p>
    </section>

    <!-- Slide 9: Getting Started -->
    <section class="slide" style="padding: 60px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
      <h2 style="font-family: Arial, sans-serif; font-size: 42px; font-weight: 700; color: #ffffff; margin: 0;">Let's Build Yours</h2>
      <p style="font-family: Arial, sans-serif; font-size: 20px; color: #94a3b8; margin: 16px 0 0 0;">I'll ask you a few questions about what you do,</p>
      <p style="font-family: Arial, sans-serif; font-size: 20px; color: #94a3b8; margin: 4px 0 0 0;">then we'll design your agent setup together.</p>
      <div style="width: 80px; height: 4px; background: #3b82f6; border-radius: 2px; margin-top: 40px;"></div>
    </section>

  </div>
</body>
</html>
"""
