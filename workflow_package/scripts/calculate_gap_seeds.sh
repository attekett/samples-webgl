#!/bin/bash
# calculate_gap_seeds.sh - Calculate how many seeds needed per category

CURRENT_SEEDS=$(ls agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
TARGET_ADDITION=${1:-25}  # Additional seeds to add
TARGET_TOTAL=$((CURRENT_SEEDS + TARGET_ADDITION))
TARGET_PCT=20  # Target 20% coverage minimum

echo "Current corpus: $CURRENT_SEEDS seeds"
echo "Target addition: $TARGET_ADDITION seeds"
echo "Target corpus: $TARGET_TOTAL seeds"
echo "Target coverage: $TARGET_PCT%"
echo ""
echo "Seeds needed per category to reach $TARGET_PCT% coverage:"
echo ""

# Function to calculate needed seeds
calculate_needed() {
    category=$1
    pattern=$2

    current_count=$(grep -l "$pattern" agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
    current_pct=$((current_count * 100 / CURRENT_SEEDS))
    target_seeds=$((TARGET_TOTAL * TARGET_PCT / 100))
    needed=$((target_seeds - current_count))

    if [ $needed -gt 0 ]; then
        printf "  %-30s Current: %2d%% (%2d/%d) → Need: %2d more seeds\n" \
            "$category:" "$current_pct" "$current_count" "$CURRENT_SEEDS" "$needed"
    else
        printf "  %-30s Current: %2d%% (%2d/%d) → ✓ Adequate\n" \
            "$category:" "$current_pct" "$current_count" "$CURRENT_SEEDS"
    fi
}

# Calculate for each category
calculate_needed "UBO" "UNIFORM_BUFFER\|uniformBlockBinding\|bindBufferBase"
calculate_needed "Transform Feedback" "TRANSFORM_FEEDBACK\|transformFeedbackVaryings\|beginTransformFeedback"
calculate_needed "Sync Objects" "fenceSync\|clientWaitSync\|waitSync"
calculate_needed "Query Objects" "createQuery\|beginQuery\|endQuery"
calculate_needed "Sampler Objects" "createSampler\|bindSampler\|samplerParameter"
calculate_needed "Integer Textures" "R32I\|RGBA32I\|R32UI\|RGBA32UI"
calculate_needed "3D Textures" "TEXTURE_3D\|texImage3D\|texStorage3D"
calculate_needed "Texture Arrays" "TEXTURE_2D_ARRAY"
calculate_needed "MRT" "drawBuffers\|COLOR_ATTACHMENT[1-9]"
calculate_needed "Depth/Stencil" "DEPTH_TEST\|STENCIL_TEST\|depthFunc\|stencilOp"

echo ""
