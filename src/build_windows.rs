use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use which::which;

const DOCKER_IMAGE: &str = "agentre-bench-mingw:latest";
const MINGW_PREFIX: &str = "x86_64-w64-mingw32";

#[derive(Debug)]
enum BuildMode {
    Native { mingw_prefix: String },
    Docker { image: String },
}

#[derive(Debug, Serialize)]
struct BuildSummary {
    total_samples: usize,
    successful: usize,
    failed: usize,
    build_mode: String,
    failed_samples: Vec<String>,
}

struct SampleConfig {
    name: String,
    source_file: PathBuf,
    output_file: PathBuf,
    extra_flags: Vec<String>,
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    let force_docker = args.contains(&"--docker-only".to_string());
    let verbose = args.contains(&"--verbose".to_string()) || args.contains(&"-v".to_string());
    let single_sample = args.iter()
        .find(|a| a.starts_with("--sample="))
        .map(|a| a.strip_prefix("--sample=").unwrap().to_string());

    println!("🔨 AgentRE-Bench Windows PE Build System");
    println!("========================================\n");

    // Detect build mode
    let build_mode = detect_build_mode(force_docker)?;
    match &build_mode {
        BuildMode::Native { mingw_prefix } => {
            println!("✓ Build mode: Native (MinGW-w64)");
            println!("  Compiler: {}-gcc", mingw_prefix);
        }
        BuildMode::Docker { image } => {
            println!("✓ Build mode: Docker");
            println!("  Image: {}", image);
        }
    }
    println!();

    // Prepare samples
    let samples = prepare_samples(single_sample.as_deref())?;
    println!("📦 Samples to compile: {}", samples.len());
    for sample in &samples {
        println!("   - {}", sample.name);
    }
    println!();

    // Create output directory
    let output_dir = Path::new("binaries_windows");
    if !output_dir.exists() {
        fs::create_dir(output_dir)
            .context("Failed to create binaries_windows directory")?;
        println!("✓ Created directory: binaries_windows/\n");
    }

    // Build each sample
    let mut successful = 0;
    let mut failed = 0;
    let mut failed_samples = Vec::new();

    for (idx, sample) in samples.iter().enumerate() {
        println!("[{}/{}] Compiling {}...", idx + 1, samples.len(), sample.name);

        match compile_sample(&build_mode, sample, verbose) {
            Ok(()) => {
                // Validate PE format
                match validate_pe_format(&sample.output_file) {
                    Ok(()) => {
                        successful += 1;
                        println!("  ✓ Success: {}", sample.output_file.display());
                    }
                    Err(e) => {
                        failed += 1;
                        failed_samples.push(sample.name.clone());
                        eprintln!("  ✗ Validation failed: {}", e);
                    }
                }
            }
            Err(e) => {
                failed += 1;
                failed_samples.push(sample.name.clone());
                eprintln!("  ✗ Compilation failed: {}", e);
            }
        }
        println!();
    }

    // Print summary
    println!("========================================");
    println!("Build Summary:");
    println!("  Total samples:  {}", samples.len());
    println!("  Successful:     {} ✓", successful);
    println!("  Failed:         {} ✗", failed);

    if !failed_samples.is_empty() {
        println!("\nFailed samples:");
        for name in &failed_samples {
            println!("  - {}", name);
        }
    }

    let summary = BuildSummary {
        total_samples: samples.len(),
        successful,
        failed,
        build_mode: match build_mode {
            BuildMode::Native { .. } => "Native MinGW".to_string(),
            BuildMode::Docker { .. } => "Docker".to_string(),
        },
        failed_samples,
    };

    // Save summary JSON
    let summary_json = serde_json::to_string_pretty(&summary)?;
    fs::write("binaries_windows/build_summary.json", summary_json)?;
    println!("\n✓ Build summary saved to binaries_windows/build_summary.json");

    if failed > 0 {
        bail!("{} sample(s) failed to build", failed);
    }

    println!("\n🎉 All binaries built successfully!");
    Ok(())
}

fn detect_build_mode(force_docker: bool) -> Result<BuildMode> {
    if force_docker {
        check_docker()?;
        return Ok(BuildMode::Docker {
            image: DOCKER_IMAGE.to_string(),
        });
    }

    // Try to find MinGW gcc
    let gcc_name = format!("{}-gcc", MINGW_PREFIX);
    if let Ok(_gcc_path) = which(&gcc_name) {
        return Ok(BuildMode::Native {
            mingw_prefix: MINGW_PREFIX.to_string(),
        });
    }

    // Fallback to Docker
    check_docker()?;
    Ok(BuildMode::Docker {
        image: DOCKER_IMAGE.to_string(),
    })
}

fn check_docker() -> Result<()> {
    Command::new("docker")
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .context("Docker is not available. Please install Docker or MinGW-w64 toolchain.")?;

    // Check if image exists
    let output = Command::new("docker")
        .args(&["images", "-q", DOCKER_IMAGE])
        .output()
        .context("Failed to check Docker images")?;

    if output.stdout.is_empty() {
        bail!(
            "Docker image '{}' not found. Please build it first:\n\
             docker build --platform linux/amd64 -t {} -f Dockerfile.mingw .",
            DOCKER_IMAGE, DOCKER_IMAGE
        );
    }

    Ok(())
}

fn prepare_samples(single_sample: Option<&str>) -> Result<Vec<SampleConfig>> {
    // MVP samples: levels 1, 2, 4, 7, 11
    let sample_names = vec![
        "level1_TCPServer",
        "level2_XorEncodedStrings",
        "level4_polymorphicReverseShell",
        "level7_DNS_TunnelReverseShell",
        "level11_ForkBombReverseShell",
    ];

    let samples = if let Some(name) = single_sample {
        if !sample_names.contains(&name) {
            bail!("Unknown sample: {}. Available samples: {:?}", name, sample_names);
        }
        vec![name]
    } else {
        sample_names
    };

    let mut configs = Vec::new();
    for name in samples {
        let source_file = PathBuf::from(format!("samples_windows/{}.c", name));
        if !source_file.exists() {
            bail!(
                "Source file not found: {}\n\
                 Please ensure Windows-specific C sources are in samples_windows/ directory.",
                source_file.display()
            );
        }

        let output_file = PathBuf::from(format!("binaries_windows/{}.exe", name));

        configs.push(SampleConfig {
            name: name.to_string(),
            source_file,
            output_file,
            extra_flags: vec!["-lws2_32".to_string()],
        });
    }

    Ok(configs)
}

fn compile_sample(mode: &BuildMode, sample: &SampleConfig, verbose: bool) -> Result<()> {
    match mode {
        BuildMode::Native { mingw_prefix } => {
            compile_native(mingw_prefix, sample, verbose)
        }
        BuildMode::Docker { image } => {
            compile_docker(image, sample, verbose)
        }
    }
}

fn compile_native(mingw_prefix: &str, sample: &SampleConfig, verbose: bool) -> Result<()> {
    let gcc = format!("{}-gcc", mingw_prefix);
    let mut cmd = Command::new(&gcc);

    cmd.arg("-O0")
        .arg("-fno-stack-protector")
        .arg("-static")
        .arg("-Wl,--subsystem,console")
        .args(&sample.extra_flags)
        .arg(&sample.source_file)
        .arg("-o")
        .arg(&sample.output_file);

    if verbose {
        println!("  Command: {} {:?}", gcc, cmd.get_args().collect::<Vec<_>>());
    }

    let output = cmd
        .output()
        .context(format!("Failed to execute {}", gcc))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        bail!("Compilation failed:\n{}", stderr);
    }

    Ok(())
}

fn compile_docker(image: &str, sample: &SampleConfig, verbose: bool) -> Result<()> {
    let project_root = env::current_dir()
        .context("Failed to get current directory")?;

    let source_rel = sample.source_file.strip_prefix(&project_root)
        .unwrap_or(&sample.source_file);
    let output_rel = sample.output_file.strip_prefix(&project_root)
        .unwrap_or(&sample.output_file);

    let docker_source = format!("/workspace/{}", source_rel.display());
    let docker_output = format!("/workspace/{}", output_rel.display());

    let mut gcc_args = vec![
        "-O0".to_string(),
        "-fno-stack-protector".to_string(),
        "-static".to_string(),
        "-Wl,--subsystem,console".to_string(),
    ];
    gcc_args.extend(sample.extra_flags.clone());
    gcc_args.push(docker_source.clone());
    gcc_args.push("-o".to_string());
    gcc_args.push(docker_output.clone());

    let mut cmd = Command::new("docker");
    cmd.arg("run")
        .arg("--rm")
        .arg("--platform")
        .arg("linux/amd64")
        .arg("-v")
        .arg(format!("{}:/workspace", project_root.display()))
        .arg(image)
        .arg("x86_64-w64-mingw32-gcc")
        .args(&gcc_args);

    if verbose {
        println!("  Docker command: docker run ... x86_64-w64-mingw32-gcc {:?}", gcc_args);
    }

    let output = cmd
        .output()
        .context("Failed to execute Docker")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        bail!("Docker compilation failed:\n{}", stderr);
    }

    Ok(())
}

fn validate_pe_format(binary: &Path) -> Result<()> {
    // Read first 2 bytes (MZ header)
    let mut file = fs::File::open(binary)
        .context(format!("Failed to open binary: {}", binary.display()))?;

    let mut magic = [0u8; 2];
    file.read_exact(&mut magic)
        .context("Failed to read PE magic bytes")?;

    if magic != [0x4D, 0x5A] {  // 'MZ' in ASCII
        bail!(
            "Invalid PE format: expected MZ header (4D 5A), got {:02X} {:02X}",
            magic[0], magic[1]
        );
    }

    // Check file size is reasonable (50KB - 10MB)
    let metadata = fs::metadata(binary)?;
    let size = metadata.len();

    if size < 50_000 {
        bail!("Binary too small: {} bytes (expected > 50KB)", size);
    }

    if size > 10_000_000 {
        bail!("Binary too large: {} bytes (expected < 10MB)", size);
    }

    Ok(())
}
