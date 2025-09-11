"""
Performance Monitor for Trading Bot Optimizations
Module pour surveiller et analyser les performances des optimisations
"""

import asyncio
import time
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict
from smart_api_cache import smart_cache
from api_coordinator import api_coordinator
from optimized_market_aggregator import optimized_market_aggregator

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Métrique de performance individuelle"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    category: str = "general"
    
    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category
        }

class PerformanceMonitor:
    """
    🔬 Moniteur de performance pour analyser l'efficacité des optimisations
    """
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetric] = []
        self.baseline_measurements = {}
        self.optimization_impact = {}
        
    async def measure_scout_performance(self, symbols: List[str]) -> Dict[str, Any]:
        """Mesure les performances du Scout optimisé"""
        start_time = time.time()
        
        # Test sans cache (simulation baseline)
        no_cache_start = time.time()
        try:
            # Simulate non-cached requests
            for symbol in symbols[:5]:  # Test with first 5 symbols
                await optimized_market_aggregator.get_comprehensive_market_data_optimized(
                    symbol, force_refresh=True
                )
        except Exception as e:
            logger.warning(f"Baseline measurement error: {e}")
        no_cache_time = time.time() - no_cache_start
        
        # Test avec cache
        cache_start = time.time()
        cache_results = await optimized_market_aggregator.get_batch_market_data_optimized(
            symbols[:5], max_age=300
        )
        cache_time = time.time() - cache_start
        
        # Calcul des métriques
        total_time = time.time() - start_time
        cache_efficiency = ((no_cache_time - cache_time) / no_cache_time) * 100 if no_cache_time > 0 else 0
        
        metrics = {
            "scout_total_time": total_time,
            "baseline_time": no_cache_time,
            "cached_time": cache_time,
            "cache_efficiency_percent": cache_efficiency,
            "symbols_processed": len(cache_results),
            "cache_hit_rate": smart_cache.get_stats()["hit_rate"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Enregistrer métriques
        self._record_metric("scout_performance", total_time, "seconds", "optimization")
        self._record_metric("cache_efficiency", cache_efficiency, "percent", "optimization")
        
        return metrics
    
    async def measure_api_coordination_impact(self, symbols: List[str]) -> Dict[str, Any]:
        """Mesure l'impact de la coordination API"""
        start_time = time.time()
        
        # Test coordination API
        coordination_stats = api_coordinator.get_coordination_metrics()
        
        # Test pipeline efficiency
        pipeline_tests = []
        for symbol in symbols[:3]:  # Test with 3 symbols
            pipeline_start = time.time()
            
            # Simulate Scout → IA1 → IA2 pipeline
            scout_data = await api_coordinator.request_scout_data(symbol)
            if scout_data:
                ia1_data = await api_coordinator.request_ia1_data(symbol, scout_data)
                pipeline_time = time.time() - pipeline_start
                
                pipeline_tests.append({
                    "symbol": symbol,
                    "pipeline_time": pipeline_time,
                    "has_scout_data": scout_data is not None,
                    "has_ia1_data": ia1_data is not None
                })
        
        total_time = time.time() - start_time
        avg_pipeline_time = sum(t["pipeline_time"] for t in pipeline_tests) / len(pipeline_tests) if pipeline_tests else 0
        
        metrics = {
            "coordination_total_time": total_time,
            "average_pipeline_time": avg_pipeline_time,
            "coordination_stats": coordination_stats,
            "pipeline_tests": pipeline_tests,
            "api_calls_prevented": coordination_stats["coordinator_metrics"]["api_calls_prevented"],
            "pipeline_reuses": coordination_stats["coordinator_metrics"]["pipeline_reuses"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Enregistrer métriques
        self._record_metric("api_coordination", total_time, "seconds", "optimization")
        self._record_metric("pipeline_reuses", metrics["pipeline_reuses"], "count", "optimization")
        
        return metrics
    
    async def measure_cache_performance(self) -> Dict[str, Any]:
        """Mesure les performances du système de cache"""
        cache_stats = smart_cache.get_stats()
        aggregator_metrics = optimized_market_aggregator.get_performance_metrics()
        
        metrics = {
            "cache_stats": cache_stats,
            "aggregator_metrics": aggregator_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        # Enregistrer métriques clés
        self._record_metric("cache_hit_rate", cache_stats["hit_rate"], "percent", "cache")
        self._record_metric("total_cache_entries", cache_stats["total_entries"], "count", "cache")
        self._record_metric("api_calls_saved", aggregator_metrics["aggregator_metrics"]["api_calls_saved"], "count", "optimization")
        
        return metrics
    
    async def run_comprehensive_performance_test(self, test_symbols: List[str] = None) -> Dict[str, Any]:
        """
        🧪 Test de performance complet du système optimisé
        """
        if not test_symbols:
            test_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX']
        
        logger.info(f"🧪 Starting comprehensive performance test with {len(test_symbols)} symbols")
        
        start_time = time.time()
        results = {}
        
        try:
            # 1. Test Scout Performance
            logger.info("📊 Testing Scout performance...")
            scout_metrics = await self.measure_scout_performance(test_symbols)
            results["scout_performance"] = scout_metrics
            
            # 2. Test API Coordination
            logger.info("🎯 Testing API coordination...")
            coordination_metrics = await self.measure_api_coordination_impact(test_symbols)
            results["api_coordination"] = coordination_metrics
            
            # 3. Test Cache Performance
            logger.info("💾 Testing cache performance...")
            cache_metrics = await self.measure_cache_performance()
            results["cache_performance"] = cache_metrics
            
            # 4. Overall Summary
            total_time = time.time() - start_time
            results["summary"] = {
                "total_test_time": total_time,
                "symbols_tested": len(test_symbols),
                "overall_cache_hit_rate": cache_metrics["cache_stats"]["hit_rate"],
                "scout_cache_efficiency": scout_metrics.get("cache_efficiency_percent", 0),
                "api_calls_prevented": coordination_metrics.get("api_calls_prevented", 0),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Performance test completed in {total_time:.2f}s")
            logger.info(f"🎯 Key Results:")
            logger.info(f"   Cache Hit Rate: {results['summary']['overall_cache_hit_rate']:.1%}")
            logger.info(f"   Scout Efficiency: {results['summary']['scout_cache_efficiency']:.1f}%")
            logger.info(f"   API Calls Saved: {results['summary']['api_calls_prevented']}")
            
        except Exception as e:
            logger.error(f"Performance test error: {e}")
            results["error"] = str(e)
            results["timestamp"] = datetime.now().isoformat()
        
        return results
    
    def _record_metric(self, name: str, value: float, unit: str, category: str = "general"):
        """Enregistre une métrique de performance"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            category=category
        )
        self.metrics_history.append(metric)
        
        # Garde seulement les 1000 dernières métriques
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Résumé des performances sur les X dernières heures"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {"message": "No metrics available for the specified period"}
        
        # Groupe par catégorie
        by_category = {}
        for metric in recent_metrics:
            if metric.category not in by_category:
                by_category[metric.category] = []
            by_category[metric.category].append(metric)
        
        summary = {
            "period_hours": hours,
            "total_metrics": len(recent_metrics),
            "categories": {}
        }
        
        for category, metrics in by_category.items():
            category_summary = {
                "count": len(metrics),
                "metrics": {}
            }
            
            # Groupe par nom de métrique
            by_name = {}
            for metric in metrics:
                if metric.name not in by_name:
                    by_name[metric.name] = []
                by_name[metric.name].append(metric.value)
            
            for name, values in by_name.items():
                category_summary["metrics"][name] = {
                    "count": len(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1]
                }
            
            summary["categories"][category] = category_summary
        
        return summary
    
    async def benchmark_vs_baseline(self, symbols: List[str]) -> Dict[str, Any]:
        """
        🏁 Benchmark des optimisations vs baseline (sans optimisations)
        """
        logger.info("🏁 Running optimization benchmark vs baseline")
        
        # Baseline: Direct API calls without cache
        baseline_start = time.time()
        baseline_results = []
        
        for symbol in symbols[:5]:  # Limit for testing
            try:
                # Simulate non-optimized fetch
                result = await optimized_market_aggregator.get_comprehensive_market_data_optimized(
                    symbol, force_refresh=True
                )
                if result:
                    baseline_results.append(result)
            except Exception as e:
                logger.warning(f"Baseline fetch error for {symbol}: {e}")
        
        baseline_time = time.time() - baseline_start
        
        # Optimized: Using cache and coordination
        optimized_start = time.time()
        optimized_results = await optimized_market_aggregator.get_batch_market_data_optimized(
            symbols[:5], max_age=60
        )
        optimized_time = time.time() - optimized_start
        
        # Calculate improvements
        time_improvement = ((baseline_time - optimized_time) / baseline_time) * 100 if baseline_time > 0 else 0
        
        benchmark = {
            "baseline": {
                "time": baseline_time,
                "results_count": len(baseline_results),
                "avg_time_per_symbol": baseline_time / len(baseline_results) if baseline_results else 0
            },
            "optimized": {
                "time": optimized_time,
                "results_count": len(optimized_results),
                "avg_time_per_symbol": optimized_time / len(optimized_results) if optimized_results else 0
            },
            "improvement": {
                "time_saved_seconds": baseline_time - optimized_time,
                "time_improvement_percent": time_improvement,
                "efficiency_multiplier": baseline_time / optimized_time if optimized_time > 0 else 0
            },
            "cache_stats": smart_cache.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🏁 Benchmark Results:")
        logger.info(f"   Baseline: {baseline_time:.2f}s")
        logger.info(f"   Optimized: {optimized_time:.2f}s") 
        logger.info(f"   Improvement: {time_improvement:.1f}% faster")
        logger.info(f"   Efficiency: {benchmark['improvement']['efficiency_multiplier']:.1f}x")
        
        return benchmark

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Export
__all__ = [
    'PerformanceMonitor',
    'PerformanceMetric',
    'performance_monitor'
]