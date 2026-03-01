# Orchestration Template

## Multi-Skill Execution Template

### Standard Orchestration Flow

```typescript
interface OrchestrationPlan {
  context: WorkContext;
  selectedSkills: SkillSelection[];
  executionOrder: ExecutionPhase[];
  qualityGates: QualityGate[];
}

interface SkillSelection {
  skill: string;
  priority: 'primary' | 'secondary';
  conditions: string[];
  timeout: number;
}

interface ExecutionPhase {
  phase: string;
  skills: string[];
  parallel: boolean;
  blocking: boolean;
}
```

---

## Execution Templates

### Template A: New Feature Development

```yaml
New_Feature_Template:
  name: "New Feature Development"
  phases:
    - phase: planning
      skills: [clean-code-mastery]
      parallel: false
      blocking: false

    - phase: testing
      skills: [tdd-guardian]
      parallel: false
      blocking: true  # Must have tests first

    - phase: implementation
      skills: [clean-code-mastery, security-shield]
      parallel: true
      blocking: true

    - phase: api_design
      skills: [api-first-design]
      parallel: false
      blocking: false
      condition: "hasApiChanges"

    - phase: review
      skills: [code-reviewer]
      parallel: false
      blocking: true

  quality_gates:
    - gate: pre-commit
      checks: [lint, type-check, test]
      blocking: true
```

---

### Template B: Bug Fix

```yaml
Bug_Fix_Template:
  name: "Bug Fix"
  phases:
    - phase: reproduce
      skills: [tdd-guardian]
      action: "Write failing test that reproduces bug"
      blocking: true

    - phase: fix
      skills: [clean-code-mastery, security-shield]
      parallel: true
      blocking: true

    - phase: verify
      skills: [tdd-guardian]
      action: "Verify test now passes"
      blocking: true

    - phase: review
      skills: [code-reviewer]
      blocking: false
```

---

### Template C: Security Patch

```yaml
Security_Patch_Template:
  name: "Security Patch"
  priority: critical
  phases:
    - phase: security_analysis
      skills: [security-shield]
      priority: 0
      blocking: true

    - phase: fix
      skills: [security-shield, clean-code-mastery]
      parallel: false
      blocking: true

    - phase: security_verify
      skills: [security-shield]
      action: "Re-scan for vulnerabilities"
      blocking: true

    - phase: test
      skills: [tdd-guardian]
      blocking: true

    - phase: review
      skills: [code-reviewer]
      blocking: true
```

---

### Template D: Refactoring

```yaml
Refactoring_Template:
  name: "Code Refactoring"
  phases:
    - phase: test_baseline
      skills: [tdd-guardian]
      action: "Ensure existing tests pass"
      blocking: true

    - phase: refactor
      skills: [clean-code-mastery, monorepo-architect]
      parallel: true
      blocking: true

    - phase: test_verify
      skills: [tdd-guardian]
      action: "Verify all tests still pass"
      blocking: true

    - phase: review
      skills: [code-reviewer]
      blocking: false
```

---

### Template E: API Change

```yaml
API_Change_Template:
  name: "API Change"
  phases:
    - phase: contract_update
      skills: [api-first-design]
      action: "Update OpenAPI spec first"
      blocking: true

    - phase: type_generation
      skills: [api-first-design]
      action: "Regenerate types"
      blocking: true

    - phase: implementation
      skills: [clean-code-mastery, security-shield]
      parallel: true
      blocking: true

    - phase: test
      skills: [tdd-guardian]
      blocking: true

    - phase: review
      skills: [code-reviewer]
      blocking: true
```

---

## Orchestration Output Template

```markdown
## Orchestration Report

### Execution Summary
- **Template Used**: {{template_name}}
- **Total Phases**: {{phase_count}}
- **Skills Invoked**: {{skill_list}}
- **Duration**: {{duration}}ms

### Phase Results

| Phase | Skills | Status | Duration | Issues |
|-------|--------|--------|----------|--------|
{{#each phases}}
| {{name}} | {{skills}} | {{status}} | {{duration}}ms | {{issue_count}} |
{{/each}}

### Quality Gates

| Gate | Threshold | Result | Pass |
|------|-----------|--------|------|
{{#each gates}}
| {{name}} | {{threshold}} | {{result}} | {{pass_icon}} |
{{/each}}

### Overall Result

- **Status**: {{overall_status}}
- **Score**: {{overall_score}}/100
- **Grade**: {{grade}}
- **Can Proceed**: {{can_proceed}}

### Next Actions

{{#each next_actions}}
- {{priority}}: {{action}}
{{/each}}
```

---

## Usage Example

```typescript
async function executeOrchestration(
  context: WorkContext,
  templateName: string
): Promise<OrchestrationResult> {
  // 1. Load template
  const template = loadOrchestrationTemplate(templateName);

  // 2. Create execution plan
  const plan = createExecutionPlan(context, template);

  // 3. Execute phases
  const results: PhaseResult[] = [];
  for (const phase of plan.executionOrder) {
    if (phase.parallel) {
      const phaseResults = await Promise.all(
        phase.skills.map(skill => executeSkill(skill, context))
      );
      results.push(...phaseResults);
    } else {
      for (const skill of phase.skills) {
        const result = await executeSkill(skill, context);
        results.push(result);

        if (phase.blocking && result.status === 'fail') {
          return { status: 'blocked', results };
        }
      }
    }
  }

  // 4. Aggregate results
  return aggregateResults(results);
}
```
