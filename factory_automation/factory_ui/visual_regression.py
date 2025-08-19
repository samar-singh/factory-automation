"""
Visual Regression Testing for Factory Automation UI
Compares current UI screenshots against baseline images
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from playwright.async_api import async_playwright
from PIL import Image, ImageChops, ImageDraw
import numpy as np

logger = logging.getLogger(__name__)


class VisualRegressionTester:
    """Visual regression testing for UI components"""
    
    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url
        self.baseline_dir = Path("ui_screenshots/baseline")
        self.current_dir = Path("ui_screenshots/current")
        self.diff_dir = Path("ui_screenshots/diff")
        
        # Create directories
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.current_dir.mkdir(parents=True, exist_ok=True)
        self.diff_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "comparisons": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "new": 0
            }
        }
    
    async def capture_baseline(self) -> Dict:
        """Capture baseline screenshots for all UI components"""
        logger.info("Capturing baseline screenshots...")
        
        async with async_playwright() as p:
            browser = await p.webkit.launch(headless=True)
            
            screenshots = []
            viewports = [
                {"name": "desktop", "width": 1920, "height": 1080},
                {"name": "tablet", "width": 768, "height": 1024},
                {"name": "mobile", "width": 375, "height": 667}
            ]
            
            for viewport in viewports:
                context = await browser.new_context(
                    viewport={"width": viewport["width"], "height": viewport["height"]}
                )
                page = await context.new_page()
                
                await page.goto(self.base_url, wait_until="networkidle")
                
                # Capture main view
                screenshot_path = self.baseline_dir / f"{viewport['name']}_main.png"
                await page.screenshot(path=str(screenshot_path))
                screenshots.append(str(screenshot_path))
                
                # Capture different tabs/states
                await self._capture_component_states(page, viewport["name"], self.baseline_dir)
                
                await context.close()
            
            await browser.close()
        
        # Save baseline metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "screenshots": screenshots,
            "url": self.base_url
        }
        
        with open(self.baseline_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Baseline captured: {len(screenshots)} screenshots")
        return metadata
    
    async def capture_current(self) -> Dict:
        """Capture current screenshots for comparison"""
        logger.info("Capturing current screenshots...")
        
        async with async_playwright() as p:
            browser = await p.webkit.launch(headless=True)
            
            screenshots = []
            viewports = [
                {"name": "desktop", "width": 1920, "height": 1080},
                {"name": "tablet", "width": 768, "height": 1024},
                {"name": "mobile", "width": 375, "height": 667}
            ]
            
            for viewport in viewports:
                context = await browser.new_context(
                    viewport={"width": viewport["width"], "height": viewport["height"]}
                )
                page = await context.new_page()
                
                await page.goto(self.base_url, wait_until="networkidle")
                
                # Capture main view
                screenshot_path = self.current_dir / f"{viewport['name']}_main.png"
                await page.screenshot(path=str(screenshot_path))
                screenshots.append(str(screenshot_path))
                
                # Capture different tabs/states
                await self._capture_component_states(page, viewport["name"], self.current_dir)
                
                await context.close()
            
            await browser.close()
        
        return {"screenshots": screenshots}
    
    async def _capture_component_states(self, page, viewport_name: str, output_dir: Path):
        """Capture different component states"""
        
        # Try to capture different tabs
        tabs = await page.query_selector_all('[role="tab"], .tab, button:has-text("tab")')
        for i, tab in enumerate(tabs[:3]):  # Capture first 3 tabs
            try:
                await tab.click()
                await page.wait_for_timeout(1000)  # Wait for transition
                
                screenshot_path = output_dir / f"{viewport_name}_tab_{i}.png"
                await page.screenshot(path=str(screenshot_path))
            except Exception as e:
                logger.warning(f"Failed to capture tab {i}: {e}")
        
        # Capture form states (if any)
        forms = await page.query_selector_all('form')
        if forms:
            screenshot_path = output_dir / f"{viewport_name}_form.png"
            await page.screenshot(path=str(screenshot_path))
        
        # Capture modal/dialog states (if any)
        modals = await page.query_selector_all('[role="dialog"], .modal')
        if modals:
            screenshot_path = output_dir / f"{viewport_name}_modal.png"
            await page.screenshot(path=str(screenshot_path))
    
    def compare_images(self, baseline_path: Path, current_path: Path) -> Tuple[bool, float, Optional[Path]]:
        """
        Compare two images and return similarity
        
        Returns:
            Tuple of (images_match, similarity_percentage, diff_image_path)
        """
        if not baseline_path.exists():
            logger.warning(f"Baseline not found: {baseline_path}")
            return False, 0.0, None
        
        if not current_path.exists():
            logger.warning(f"Current image not found: {current_path}")
            return False, 0.0, None
        
        # Open images
        baseline = Image.open(baseline_path).convert('RGB')
        current = Image.open(current_path).convert('RGB')
        
        # Resize if dimensions don't match
        if baseline.size != current.size:
            logger.warning(f"Size mismatch: {baseline.size} vs {current.size}")
            current = current.resize(baseline.size, Image.Resampling.LANCZOS)
        
        # Calculate difference
        diff = ImageChops.difference(baseline, current)
        
        # Calculate similarity percentage
        diff_array = np.array(diff)
        diff_sum = np.sum(diff_array)
        max_diff = 255 * diff_array.size
        similarity = 100 * (1 - diff_sum / max_diff)
        
        # Determine if images match (threshold: 98% similarity)
        threshold = 98.0
        images_match = similarity >= threshold
        
        # Create diff image if they don't match
        diff_path = None
        if not images_match:
            # Create visual diff
            diff_img = self._create_diff_image(baseline, current, diff)
            
            # Save diff image
            diff_filename = f"diff_{baseline_path.stem}.png"
            diff_path = self.diff_dir / diff_filename
            diff_img.save(diff_path)
            
            logger.info(f"Diff image saved: {diff_path}")
        
        return images_match, similarity, diff_path
    
    def _create_diff_image(self, baseline: Image, current: Image, diff: Image) -> Image:
        """Create a visual diff image showing differences"""
        # Create a composite image showing baseline, current, and diff
        width = baseline.width
        height = baseline.height
        
        # Create composite image (3 images side by side)
        composite = Image.new('RGB', (width * 3, height + 50), color='white')
        
        # Add images
        composite.paste(baseline, (0, 50))
        composite.paste(current, (width, 50))
        
        # Enhance diff for visibility
        diff_enhanced = Image.new('RGB', (width, height), color='white')
        diff_array = np.array(diff)
        
        # Highlight differences in red
        mask = np.any(diff_array > 10, axis=2)  # Threshold for visible difference
        diff_highlighted = np.array(baseline)
        diff_highlighted[mask] = [255, 0, 0]  # Red for differences
        
        diff_enhanced = Image.fromarray(diff_highlighted.astype('uint8'))
        composite.paste(diff_enhanced, (width * 2, 50))
        
        # Add labels
        draw = ImageDraw.Draw(composite)
        try:
            from PIL import ImageFont
            font = ImageFont.load_default()
        except:
            font = None
        
        draw.text((width // 2 - 30, 10), "BASELINE", fill="black", font=font)
        draw.text((width + width // 2 - 30, 10), "CURRENT", fill="black", font=font)
        draw.text((width * 2 + width // 2 - 30, 10), "DIFFERENCE", fill="red", font=font)
        
        return composite
    
    async def run_comparison(self) -> Dict:
        """Run full visual regression test"""
        logger.info("Starting visual regression testing...")
        
        # Check if baseline exists
        baseline_metadata_path = self.baseline_dir / "metadata.json"
        if not baseline_metadata_path.exists():
            logger.warning("No baseline found. Creating baseline...")
            await self.capture_baseline()
            return {
                "status": "baseline_created",
                "message": "Baseline screenshots created. Run again to compare."
            }
        
        # Capture current screenshots
        await self.capture_current()
        
        # Compare all screenshots
        baseline_files = sorted(self.baseline_dir.glob("*.png"))
        
        for baseline_file in baseline_files:
            current_file = self.current_dir / baseline_file.name
            
            if not current_file.exists():
                self.results["comparisons"].append({
                    "name": baseline_file.stem,
                    "status": "new",
                    "message": f"New screenshot: {baseline_file.name}"
                })
                self.results["summary"]["new"] += 1
                continue
            
            # Compare images
            match, similarity, diff_path = self.compare_images(baseline_file, current_file)
            
            comparison = {
                "name": baseline_file.stem,
                "baseline": str(baseline_file),
                "current": str(current_file),
                "similarity": round(similarity, 2),
                "match": match,
                "status": "passed" if match else "failed"
            }
            
            if diff_path:
                comparison["diff"] = str(diff_path)
            
            self.results["comparisons"].append(comparison)
            
            if match:
                self.results["summary"]["passed"] += 1
            else:
                self.results["summary"]["failed"] += 1
            
            self.results["summary"]["total"] += 1
        
        return self.results
    
    def print_report(self):
        """Print human-readable regression test report"""
        print("\n" + "="*60)
        print("VISUAL REGRESSION TEST REPORT")
        print("="*60)
        print(f"Timestamp: {self.results['timestamp']}")
        print("\n" + "-"*60)
        print("SUMMARY")
        print("-"*60)
        
        summary = self.results["summary"]
        print(f"Total Comparisons: {summary['total']}")
        print(f"  ✅ Passed: {summary['passed']}")
        print(f"  ❌ Failed: {summary['failed']}")
        print(f"  🆕 New: {summary['new']}")
        
        # Calculate pass rate
        if summary['total'] > 0:
            pass_rate = (summary['passed'] / summary['total']) * 100
            print(f"\nPass Rate: {pass_rate:.1f}%")
        
        # Show failed comparisons
        if summary['failed'] > 0:
            print("\n" + "-"*60)
            print("FAILED COMPARISONS")
            print("-"*60)
            
            for comp in self.results["comparisons"]:
                if comp.get("status") == "failed":
                    print(f"\n❌ {comp['name']}")
                    print(f"   Similarity: {comp.get('similarity', 0):.1f}%")
                    if comp.get("diff"):
                        print(f"   Diff Image: {comp['diff']}")
        
        # Show new screenshots
        if summary['new'] > 0:
            print("\n" + "-"*60)
            print("NEW SCREENSHOTS")
            print("-"*60)
            
            for comp in self.results["comparisons"]:
                if comp.get("status") == "new":
                    print(f"🆕 {comp.get('message', comp['name'])}")
        
        print("\n" + "="*60)
        
        # Overall result
        if summary['failed'] > 0:
            print("❌ VISUAL REGRESSION DETECTED")
            print("Review diff images in: ui_screenshots/diff/")
        elif summary['new'] > 0:
            print("🆕 NEW SCREENSHOTS DETECTED")
            print("Update baseline if these are expected changes")
        else:
            print("✅ ALL VISUAL TESTS PASSED")
        
        print("="*60 + "\n")
    
    def update_baseline(self):
        """Update baseline with current screenshots"""
        logger.info("Updating baseline screenshots...")
        
        # Copy current to baseline
        import shutil
        
        current_files = self.current_dir.glob("*.png")
        for current_file in current_files:
            baseline_file = self.baseline_dir / current_file.name
            shutil.copy2(current_file, baseline_file)
            logger.info(f"Updated: {baseline_file.name}")
        
        # Update metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "updated": True,
            "url": self.base_url
        }
        
        with open(self.baseline_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        print("✅ Baseline updated successfully")


async def main():
    """Run visual regression testing from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Visual Regression Testing")
    parser.add_argument("--url", default="http://localhost:7860", help="Application URL")
    parser.add_argument("--compare", action="store_true", help="Run comparison")
    parser.add_argument("--baseline", action="store_true", help="Create/update baseline")
    parser.add_argument("--update", action="store_true", help="Update baseline with current")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    tester = VisualRegressionTester(base_url=args.url)
    
    if args.baseline:
        # Create baseline
        await tester.capture_baseline()
        print("✅ Baseline created successfully")
    
    elif args.update:
        # Update baseline
        await tester.capture_current()
        tester.update_baseline()
    
    else:
        # Run comparison (default)
        results = await tester.run_comparison()
        tester.print_report()
        
        # Save results
        with open("visual_regression_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        # Exit with appropriate code
        if results.get("status") == "baseline_created":
            print("\n📸 Baseline created. Run again to compare.")
            exit(0)
        elif results["summary"]["failed"] > 0:
            exit(1)
        else:
            exit(0)


if __name__ == "__main__":
    asyncio.run(main())