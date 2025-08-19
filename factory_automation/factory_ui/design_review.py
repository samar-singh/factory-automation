"""
Design Review System for Factory Automation UI
Automated checks for UI consistency, accessibility, and performance
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class DesignReviewAgent:
    """Automated design review agent for UI validation"""

    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "screenshots": [],
            "issues": {
                "blockers": [],
                "high_priority": [],
                "medium_priority": [],
                "low_priority": [],
                "suggestions": []
            },
            "metrics": {}
        }
        self.screenshot_dir = Path("ui_screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)

    async def run_full_review(self) -> Dict:
        """Run comprehensive design review"""
        logger.info("Starting comprehensive UI design review...")
        
        async with async_playwright() as p:
            browser = await p.webkit.launch(headless=True)
            
            try:
                # Test multiple viewport sizes
                viewports = [
                    {"name": "mobile", "width": 375, "height": 667},
                    {"name": "tablet", "width": 768, "height": 1024},
                    {"name": "desktop", "width": 1920, "height": 1080}
                ]
                
                for viewport in viewports:
                    logger.info(f"Testing {viewport['name']} viewport...")
                    context = await browser.new_context(
                        viewport={"width": viewport["width"], "height": viewport["height"]}
                    )
                    page = await context.new_page()
                    
                    # Run checks for this viewport
                    await self._run_viewport_checks(page, viewport["name"])
                    
                    await context.close()
                
                # Generate summary
                self._generate_summary()
                
            finally:
                await browser.close()
        
        return self.results

    async def _run_viewport_checks(self, page, viewport_name: str):
        """Run all checks for a specific viewport"""
        
        # Navigate to application
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            # Wait for Gradio to fully load
            await page.wait_for_timeout(3000)
        except Exception as e:
            self.results["issues"]["blockers"].append(
                f"Failed to load application on {viewport_name}: {str(e)}"
            )
            return
        
        # Check each major component
        await self._check_visual_hierarchy(page, viewport_name)
        await self._check_accessibility(page, viewport_name)
        await self._check_interactions(page, viewport_name)
        await self._check_responsiveness(page, viewport_name)
        await self._check_performance(page, viewport_name)
        await self._capture_screenshots(page, viewport_name)

    async def _check_visual_hierarchy(self, page, viewport_name: str):
        """Check visual hierarchy and design consistency"""
        logger.info(f"Checking visual hierarchy for {viewport_name}...")
        
        checks = []
        
        # Check for gradient cards visibility
        gradient_cards = await page.query_selector_all('[style*="gradient"]')
        if not gradient_cards:
            checks.append({
                "status": "warning",
                "message": "Gradient cards not found or not styled properly"
            })
        
        # Check color contrast for text
        contrast_check = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                const issues = [];
                
                elements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const bg = style.backgroundColor;
                    const color = style.color;
                    
                    // Simple contrast check (would need proper WCAG calculation)
                    if (bg && color && bg !== 'rgba(0, 0, 0, 0)') {
                        // Add to issues if contrast seems low
                        // This is simplified - real implementation would calculate actual contrast ratio
                    }
                });
                
                return issues;
            }
        """)
        
        # Check font sizes for readability
        font_check = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                const tooSmall = [];
                
                elements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const fontSize = parseInt(style.fontSize);
                    
                    if (fontSize && fontSize < 12 && el.textContent.trim()) {
                        tooSmall.push({
                            text: el.textContent.substring(0, 50),
                            size: fontSize
                        });
                    }
                });
                
                return tooSmall;
            }
        """)
        
        if font_check:
            self.results["issues"]["medium_priority"].append({
                "viewport": viewport_name,
                "issue": "Text too small for readability",
                "details": font_check[:5]  # Limit to first 5 instances
            })
        
        self.results["checks"][f"visual_hierarchy_{viewport_name}"] = {
            "status": "pass" if not checks else "warning",
            "checks": checks
        }

    async def _check_accessibility(self, page, viewport_name: str):
        """Check accessibility compliance"""
        logger.info(f"Checking accessibility for {viewport_name}...")
        
        # Check for ARIA labels
        aria_check = await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('button');
                const links = document.querySelectorAll('a');
                const inputs = document.querySelectorAll('input');
                
                const missing = [];
                
                [...buttons, ...links, ...inputs].forEach(el => {
                    if (!el.getAttribute('aria-label') && !el.textContent.trim()) {
                        missing.push(el.tagName.toLowerCase());
                    }
                });
                
                return missing;
            }
        """)
        
        if aria_check:
            self.results["issues"]["high_priority"].append({
                "viewport": viewport_name,
                "issue": "Missing ARIA labels",
                "elements": aria_check[:10]
            })
        
        # Check focus indicators
        focus_check = await page.evaluate("""
            () => {
                const interactive = document.querySelectorAll('button, a, input, select, textarea');
                const noFocus = [];
                
                interactive.forEach(el => {
                    el.focus();
                    const style = window.getComputedStyle(el);
                    if (!style.outline && !style.boxShadow) {
                        noFocus.push(el.tagName.toLowerCase());
                    }
                });
                
                return noFocus;
            }
        """)
        
        if focus_check:
            self.results["issues"]["high_priority"].append({
                "viewport": viewport_name,
                "issue": "Missing focus indicators",
                "elements": focus_check[:10]
            })
        
        # Check touch target sizes for mobile
        if viewport_name == "mobile":
            touch_targets = await page.evaluate("""
                () => {
                    const interactive = document.querySelectorAll('button, a');
                    const tooSmall = [];
                    
                    interactive.forEach(el => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 44 || rect.height < 44) {
                            tooSmall.push({
                                element: el.tagName.toLowerCase(),
                                size: `${rect.width}x${rect.height}`
                            });
                        }
                    });
                    
                    return tooSmall;
                }
            """)
            
            if touch_targets:
                self.results["issues"]["high_priority"].append({
                    "viewport": viewport_name,
                    "issue": "Touch targets too small (minimum 44x44px)",
                    "elements": touch_targets[:10]
                })

    async def _check_interactions(self, page, viewport_name: str):
        """Check interactive elements and user flows"""
        logger.info(f"Checking interactions for {viewport_name}...")
        
        # Check if tabs are clickable
        tabs = await page.query_selector_all('[role="tab"], .tab, button[class*="tab"]')
        if tabs:
            for tab in tabs[:3]:  # Test first 3 tabs
                try:
                    await tab.click(timeout=1000)
                    await page.wait_for_timeout(500)  # Wait for transition
                except Exception as e:
                    self.results["issues"]["high_priority"].append({
                        "viewport": viewport_name,
                        "issue": "Tab not clickable or responsive",
                        "error": str(e)
                    })
        
        # Check form inputs
        inputs = await page.query_selector_all('input[type="text"], textarea')
        for input_el in inputs[:3]:  # Test first 3 inputs
            try:
                await input_el.click()
                await input_el.type("Test input", delay=50)
                await input_el.clear()
            except Exception as e:
                self.results["issues"]["medium_priority"].append({
                    "viewport": viewport_name,
                    "issue": "Input field not responsive",
                    "error": str(e)
                })

    async def _check_responsiveness(self, page, viewport_name: str):
        """Check responsive design and layout"""
        logger.info(f"Checking responsiveness for {viewport_name}...")
        
        # Check for horizontal scrolling
        horizontal_scroll = await page.evaluate("""
            () => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }
        """)
        
        if horizontal_scroll:
            self.results["issues"]["high_priority"].append({
                "viewport": viewport_name,
                "issue": "Horizontal scrolling detected - content overflow"
            })
        
        # Check for overlapping elements
        overlap_check = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('div, button, input');
                const overlaps = [];
                
                for (let i = 0; i < elements.length - 1; i++) {
                    const rect1 = elements[i].getBoundingClientRect();
                    for (let j = i + 1; j < elements.length; j++) {
                        const rect2 = elements[j].getBoundingClientRect();
                        
                        if (!(rect1.right < rect2.left || 
                              rect1.left > rect2.right || 
                              rect1.bottom < rect2.top || 
                              rect1.top > rect2.bottom)) {
                            // Elements overlap
                            overlaps.push({
                                element1: elements[i].className || elements[i].tagName,
                                element2: elements[j].className || elements[j].tagName
                            });
                        }
                    }
                }
                
                return overlaps.slice(0, 5);  // Return first 5 overlaps
            }
        """)
        
        if overlap_check:
            self.results["issues"]["medium_priority"].append({
                "viewport": viewport_name,
                "issue": "Overlapping elements detected",
                "details": overlap_check
            })

    async def _check_performance(self, page, viewport_name: str):
        """Check performance metrics"""
        logger.info(f"Checking performance for {viewport_name}...")
        
        # Measure page load time
        metrics = await page.evaluate("""
            () => {
                const perf = window.performance;
                const timing = perf.timing;
                
                return {
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    loadComplete: timing.loadEventEnd - timing.navigationStart,
                    firstPaint: perf.getEntriesByType('paint')[0]?.startTime || 0
                };
            }
        """)
        
        self.results["metrics"][viewport_name] = metrics
        
        # Check for performance issues
        if metrics["loadComplete"] > 3000:
            self.results["issues"]["high_priority"].append({
                "viewport": viewport_name,
                "issue": f"Page load too slow: {metrics['loadComplete']}ms (target: <3000ms)"
            })
        
        # Check console for errors
        console_messages = []
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type,
            "text": msg.text
        }))
        
        await page.reload()
        await page.wait_for_timeout(2000)
        
        errors = [msg for msg in console_messages if msg["type"] == "error"]
        if errors:
            self.results["issues"]["high_priority"].append({
                "viewport": viewport_name,
                "issue": "Console errors detected",
                "errors": errors[:5]
            })

    async def _capture_screenshots(self, page, viewport_name: str):
        """Capture screenshots of different UI states"""
        logger.info(f"Capturing screenshots for {viewport_name}...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Main dashboard
        screenshot_path = self.screenshot_dir / f"{viewport_name}_{timestamp}_main.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        self.results["screenshots"].append(str(screenshot_path))
        
        # Try to capture different tabs
        tabs = await page.query_selector_all('[role="tab"], .tab')
        for i, tab in enumerate(tabs[:3]):
            try:
                await tab.click()
                await page.wait_for_timeout(1000)
                
                screenshot_path = self.screenshot_dir / f"{viewport_name}_{timestamp}_tab{i}.png"
                await page.screenshot(path=str(screenshot_path), full_page=False)
                self.results["screenshots"].append(str(screenshot_path))
            except:
                pass

    def _generate_summary(self):
        """Generate summary of design review"""
        total_issues = sum(len(issues) for issues in self.results["issues"].values())
        
        self.results["summary"] = {
            "total_issues": total_issues,
            "blockers": len(self.results["issues"]["blockers"]),
            "high_priority": len(self.results["issues"]["high_priority"]),
            "medium_priority": len(self.results["issues"]["medium_priority"]),
            "low_priority": len(self.results["issues"]["low_priority"]),
            "suggestions": len(self.results["issues"]["suggestions"]),
            "screenshots_captured": len(self.results["screenshots"])
        }
        
        # Overall status
        if self.results["issues"]["blockers"]:
            self.results["overall_status"] = "BLOCKED"
        elif self.results["issues"]["high_priority"]:
            self.results["overall_status"] = "NEEDS_FIXES"
        elif self.results["issues"]["medium_priority"]:
            self.results["overall_status"] = "MINOR_ISSUES"
        else:
            self.results["overall_status"] = "PASSED"

    def print_report(self):
        """Print human-readable report"""
        print("\n" + "="*60)
        print("UI DESIGN REVIEW REPORT")
        print("="*60)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Overall Status: {self.results.get('overall_status', 'UNKNOWN')}")
        print("\n" + "-"*60)
        print("SUMMARY")
        print("-"*60)
        
        summary = self.results.get("summary", {})
        print(f"Total Issues: {summary.get('total_issues', 0)}")
        print(f"  - Blockers: {summary.get('blockers', 0)}")
        print(f"  - High Priority: {summary.get('high_priority', 0)}")
        print(f"  - Medium Priority: {summary.get('medium_priority', 0)}")
        print(f"  - Low Priority: {summary.get('low_priority', 0)}")
        print(f"  - Suggestions: {summary.get('suggestions', 0)}")
        print(f"Screenshots Captured: {summary.get('screenshots_captured', 0)}")
        
        # Print issues by priority
        if self.results["issues"]["blockers"]:
            print("\n" + "-"*60)
            print("🚨 BLOCKERS")
            print("-"*60)
            for issue in self.results["issues"]["blockers"]:
                print(f"  • {issue}")
        
        if self.results["issues"]["high_priority"]:
            print("\n" + "-"*60)
            print("⚠️  HIGH PRIORITY")
            print("-"*60)
            for issue in self.results["issues"]["high_priority"]:
                if isinstance(issue, dict):
                    print(f"  • [{issue.get('viewport', 'N/A')}] {issue.get('issue', 'N/A')}")
                    if 'details' in issue:
                        print(f"    Details: {issue['details'][:100]}...")
                else:
                    print(f"  • {issue}")
        
        if self.results["issues"]["medium_priority"]:
            print("\n" + "-"*60)
            print("⚡ MEDIUM PRIORITY")
            print("-"*60)
            for issue in self.results["issues"]["medium_priority"][:5]:  # Show first 5
                if isinstance(issue, dict):
                    print(f"  • [{issue.get('viewport', 'N/A')}] {issue.get('issue', 'N/A')}")
                else:
                    print(f"  • {issue}")
        
        # Performance metrics
        if self.results.get("metrics"):
            print("\n" + "-"*60)
            print("📊 PERFORMANCE METRICS")
            print("-"*60)
            for viewport, metrics in self.results["metrics"].items():
                print(f"\n{viewport.upper()}:")
                print(f"  • DOM Content Loaded: {metrics.get('domContentLoaded', 'N/A')}ms")
                print(f"  • Page Load Complete: {metrics.get('loadComplete', 'N/A')}ms")
                print(f"  • First Paint: {metrics.get('firstPaint', 'N/A')}ms")
        
        print("\n" + "="*60)
        print("END OF REPORT")
        print("="*60 + "\n")

    def save_report(self, filepath: Optional[str] = None):
        """Save report to JSON file"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"ui_review_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Report saved to {filepath}")
        return filepath


async def main():
    """Run design review from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run UI Design Review")
    parser.add_argument("--url", default="http://localhost:7860", help="Application URL")
    parser.add_argument("--save", action="store_true", help="Save report to file")
    parser.add_argument("--output", help="Output file path for report")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run review
    reviewer = DesignReviewAgent(base_url=args.url)
    results = await reviewer.run_full_review()
    
    # Print report
    reviewer.print_report()
    
    # Save if requested
    if args.save:
        filepath = reviewer.save_report(args.output)
        print(f"\n✅ Report saved to: {filepath}")
    
    # Exit with appropriate code
    status = results.get("overall_status", "UNKNOWN")
    if status == "BLOCKED":
        sys.exit(1)
    elif status == "NEEDS_FIXES":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())