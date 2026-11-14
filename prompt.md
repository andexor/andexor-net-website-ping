### Description

As an SRE,
I want to count pings from links
So that I can distinguish between interactive and non-interactive use.

### Acceptance Criteria

A service will be created that will be called by browsers whenever an interactive user clicks a link.
This could happen with some automated tests, but mostly it will indicate that a human is using the site.

### Technical Details

After this is created, and andexor-net-website is updated for links to send pings,
then we can monitor the pings and compare them to page views.
This will help us to distinguish between interactive and non-interactive users.

See PRD.md for details.
Please update README.md, PRD.md, setup.md, as necessary
for consistency and fill in any gaps you might find.
Ask me any questions you need for clarity.
Please adapt CICD.md for use in this repo, using data from PRD.md.
Automate everything that can be automated.
For anything that requires manual configuration, add that to a checklist and save the file for review.
Try to batch any manual work together, either at the begining or at the end of the setup process
so it can all be done at once if possible.
