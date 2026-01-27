# Workflow Package Installation Checklist

Use this checklist when setting up the workflow package in a new project.

---

## Pre-Installation

- [ ] Project has `agent_outputs/` directory with seed files
- [ ] Project has `run_tests.sh` or equivalent test runner
- [ ] Project has `docs/` directory for documentation
- [ ] Git repository is initialized (if using version control)

---

## Installation

- [ ] Copy `workflow_package/` to project root
- [ ] Run `chmod +x workflow_package/scripts/*.sh`
- [ ] Verify scripts are executable: `ls -l workflow_package/scripts/`

---

## Verification

- [ ] Test analyze_corpus.sh: `./workflow_package/scripts/analyze_corpus.sh`
- [ ] Test feature_matrix.sh: `./workflow_package/scripts/feature_matrix.sh`
- [ ] Verify output shows correct file counts
- [ ] Check that grep patterns match your seed files

---

## Customization

- [ ] Update file patterns if seeds don't match `mutation_b*.html`
- [ ] Adjust `TARGET_PCT` in `calculate_gap_seeds.sh` if needed (default: 20%)
- [ ] Add custom feature categories to `feature_matrix.sh` if desired
- [ ] Review and customize enhancement plan template

---

## First Run

- [ ] Generate initial statistics: `./workflow_package/scripts/analyze_corpus.sh > stats.txt`
- [ ] Review feature matrix: `./workflow_package/scripts/feature_matrix.sh >> stats.txt`
- [ ] Calculate gaps: `./workflow_package/scripts/calculate_gap_seeds.sh 25`
- [ ] Review `ITERATIVE_CORPUS_EXPANSION_WORKFLOW.md` for detailed workflow

---

## Documentation

- [ ] Read `workflow_package/README.md`
- [ ] Read `ITERATIVE_CORPUS_EXPANSION_WORKFLOW.md`
- [ ] Review `examples/QUICK_START_EXAMPLE.md`
- [ ] Check `RADAMSA_INTEGRATION_GUIDE.md` for fuzzing

---

## Integration Test

- [ ] Create a test enhancement plan using template
- [ ] Run validation on existing seeds: `./workflow_package/scripts/validate_new_seeds.sh 1 10`
- [ ] Verify analyze_failures.sh works: `./workflow_package/scripts/analyze_failures.sh`
- [ ] Test strip_console_logs.sh on a copy: `cp agent_outputs/mutation_b1_s1*.html /tmp/ && ./workflow_package/scripts/strip_console_logs.sh 1 1`

---

## Optional

- [ ] Set up git hooks for automated validation
- [ ] Create project-specific wrapper scripts
- [ ] Integrate with CI/CD pipeline
- [ ] Schedule periodic corpus analysis

---

## Troubleshooting Checklist

If scripts don't work, check:

- [ ] Working directory is project root (where run_tests.sh exists)
- [ ] Scripts are executable (`chmod +x`)
- [ ] Seed files match expected patterns (`mutation_b*.html`)
- [ ] Required tools installed: bash, grep, sed, awk, bc (optional)
- [ ] JSON test results exist (`.json` files in `agent_outputs/`)

---

## Support

- Review script comments for inline documentation
- Check `workflow_package/README.md` for detailed usage
- See `examples/QUICK_START_EXAMPLE.md` for step-by-step walkthrough
- Refer to `ITERATIVE_CORPUS_EXPANSION_WORKFLOW.md` for complete process

---

## Success Indicators

You'll know the package is working when:

- ✅ `analyze_corpus.sh` shows correct file counts and statistics
- ✅ `feature_matrix.sh` displays coverage percentages
- ✅ `calculate_gap_seeds.sh` identifies low-coverage categories
- ✅ `validate_new_seeds.sh` runs tests and reports pass/fail
- ✅ Complete workflow can be executed start to finish

---

## Next Steps

After installation and verification:

1. Generate baseline statistics
2. Create first enhancement plan
3. Run Round 1 expansion
4. Document results
5. Repeat process for continuous improvement

Good luck with your corpus expansion!
