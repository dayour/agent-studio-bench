# Policy Advisor Scenario

This dataset provides an enterprise-oriented sample scenario for the marketplace framework.

It models a simple HR and legal "policy advisor" domain where requesters look for an advisor that can answer policy questions using connected knowledge systems such as SharePoint, ServiceNow, employee handbook content, and case-management workflows.

## Concept Mapping

The current framework still uses marketplace-shaped data structures. This dataset maps them as follows:

- `customer` -> employee, HR partner, or legal operations requester
- `business` -> policy advisor agent or advisory desk
- `menu_features` -> policy topics or advisory tasks the agent can cover
- `amenity_features` -> connected systems, content sources, or workflow capabilities
- `min_price_factor` -> willingness or ability to negotiate the final advisory package cost

## Included Requests

- Leave and accommodation case review
- Contractor conflict-of-interest and outside employment triage
- Litigation hold and retention exception guidance

## Connected Knowledge Examples

- SharePoint Policy Library
- ServiceNow HR Cases
- Contract Repository
- Employee Handbook
- Case Management
- Approval Workflow
- Audit Trail
- Teams Escalation

## Running the Dataset

From the repository root:

```powershell
.\\.venv\\Scripts\\magentic-marketplace.exe run data\\policy_advisor_3_9 --experiment-name policy_advisor_3_9 --env-file .env --override-db
.\\.venv\\Scripts\\magentic-marketplace.exe analyze policy_advisor_3_9
```

## Validation

You can validate the hand-authored dataset shape with:

```powershell
cd data\\data_generation_scripts
..\\..\\.venv\\Scripts\\python.exe validate.py -f ..\\features\\policy_advisor ..\\policy_advisor_3_9
```

NOTE: `baseline_utilities.py` currently requires `numpy`, which is not available in the active project environment by default, so baseline JSON generation may need a separate dependency step if you want that artifact too.
