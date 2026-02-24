const fs = require('fs');
const path = require('path');
const webidl2 = require('webidl2');

const CACHE_DIR = path.join(__dirname, '.idl_cache');

/**
 * A more robust stateful parser for the Khronos WebGL IDL files.
 * It tracks the "current block" defined by /* ... *\/ comments.
 */
function extractConstantsWithContext(idlText) {
    const lines = idlText.split('\n');
    let currentRole = 'General';
    const results = [];
    
    // Tracks if we are currently inside an interface that contains GLenum constants
    let insideRelevantInterface = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // Detect interface boundaries
        if (line.includes('interface mixin WebGLRenderingContextBase') || 
            line.includes('interface mixin WebGL2RenderingContextBase')) {
            insideRelevantInterface = true;
        }
        if (insideRelevantInterface && line === '};') {
            insideRelevantInterface = false;
        }

        if (!insideRelevantInterface) continue;

        // Detect Role-defining comments: /* RoleName */
        // We look for comments that are on their own line or before a constant
        const roleMatch = line.match(/^\/\*\s*([^*\/]+?)\s*\*\//);
        if (roleMatch && !line.includes('const')) {
            const potentialRole = roleMatch[1].trim();
            // Filter out noise like "not supported" or "Ideally the typedef"
            if (!potentialRole.toLowerCase().includes('supported') && 
                !potentialRole.toLowerCase().includes('ideally')) {
                currentRole = potentialRole;
            }
        }

        // Detect Constants
        const constMatch = line.match(/const GLenum\s+([A-Z0-9_]+)\s*=\s*(0x[0-9A-F]+|[0-9]+)/i);
        if (constMatch) {
            results.push({
                name: constMatch[1],
                value: constMatch[2],
                role: currentRole
            });
        }
    }
    return results;
}

async function run() {
    const w1 = fs.readFileSync(path.join(CACHE_DIR, 'webgl1.idl'), 'utf8');
    const w2 = fs.readFileSync(path.join(CACHE_DIR, 'webgl2.idl'), 'utf8');

    const constants1 = extractConstantsWithContext(w1);
    const constants2 = extractConstantsWithContext(w2);

    const merged = new Map();
    [...constants1, ...constants2].forEach(c => {
        if (!merged.has(c.name)) {
            merged.set(c.name, { ...c, roles: new Set() });
        }
        merged.get(c.name).roles.add(c.role);
    });

    console.log(`\n--- BLOCK SCRAPING TEST ---`);
    console.log(`Total Constants Processed: ${merged.size}`);

    const roleStats = new Map();
    let orphans = 0;

    for (const [name, data] of merged) {
        if (data.roles.has('General')) {
            orphans++;
        } else {
            data.roles.forEach(r => {
                roleStats.set(r, (roleStats.get(r) || 0) + 1);
            });
        }
    }

    console.log(`Successfully Tagged: ${merged.size - orphans}`);
    console.log(`Remaining Orphans (General/Untagged): ${orphans}`);
    console.log(`Automation Rate: ${(((merged.size - orphans) / merged.size) * 100).toFixed(1)}%`);

    console.log(`\nTop 15 Automatically Discovered Roles:`);
    const sorted = [...roleStats.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15);
    sorted.forEach(([role, count]) => {
        console.log(`  [${count.toString().padStart(3)}] ${role}`);
    });

    console.log(`\nSample of "Orphans" (still need manual/Tier B mapping):`);
    const orphanList = [...merged.values()].filter(v => v.roles.has('General')).slice(0, 10);
    orphanList.forEach(o => console.log(`  - ${o.name} (${o.value})`));
}

run().catch(console.error);
