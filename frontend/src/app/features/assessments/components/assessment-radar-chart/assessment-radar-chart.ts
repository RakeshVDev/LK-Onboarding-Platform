import { CommonModule } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  computed,
  effect,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import {
  Chart,
  ChartConfiguration,
  Filler,
  Legend,
  LineElement,
  PointElement,
  RadarController,
  RadialLinearScale,
  Tooltip,
} from 'chart.js';

Chart.register(
  RadarController,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

export interface RadarChartSeries {
  id: string;
  label: string;
  values: number[];
  borderColor: string;
  backgroundColor: string;
  dashed?: boolean;
  pointRadius?: number;
  seriesType?: 'candidate' | 'cohort_average' | 'benchmark' | string;
  overallPercentage?: number;
}

@Component({
  selector: 'app-assessment-radar-chart',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './assessment-radar-chart.html',
  styleUrl: './assessment-radar-chart.scss',
})
export class AssessmentRadarChartComponent {
  private readonly destroyRef = inject(DestroyRef);

  title = input<string>('Multi-Dimensional Competency Profile');
  subtitle = input<string>('');
  axes = input<string[]>([]);
  series = input<RadarChartSeries[]>([]);
  height = input<number>(360);
  compact = input<boolean>(false);
  showLegendToggles = input<boolean>(true);
  allowBenchmarkToggle = input<boolean>(false);
  benchmarkValues = input<number[]>([]);
  emptyMessage = input<string>(
    'Complete or evaluate an assessment session to render radar analytics.'
  );

  readonly canvasRef = viewChild<ElementRef<HTMLCanvasElement>>('radarCanvas');

  readonly hiddenSeriesIds = signal<Set<string>>(new Set());
  readonly showBenchmark = signal<boolean>(true);
  readonly viewMode = signal<'radar' | 'table'>('radar');
  readonly canvasUnavailable = signal<boolean>(false);

  private chartInstance: Chart<'radar'> | null = null;

  readonly hasEnoughAxes = computed(() => this.axes().length >= 3);

  readonly effectiveSeries = computed<RadarChartSeries[]>(() => {
    const base = [...this.series()];
    if (
      this.allowBenchmarkToggle() &&
      this.showBenchmark() &&
      this.axes().length > 0
    ) {
      const bench = this.benchmarkValues();
      const values =
        bench.length === this.axes().length
          ? bench
          : this.axes().map(() => 75);
      base.push({
        id: '__benchmark_target__',
        label: 'Readiness Target (75%)',
        values,
        borderColor: '#64748b',
        backgroundColor: 'rgba(100, 116, 139, 0.06)',
        dashed: true,
        pointRadius: 2,
        seriesType: 'benchmark',
      });
    }
    return base;
  });

  readonly visibleSeries = computed<RadarChartSeries[]>(() => {
    const effective = this.effectiveSeries();
    const hidden = this.hiddenSeriesIds();
    const filtered = effective.filter((item) => !hidden.has(item.id));
    if (filtered.length > 0 || effective.length === 0) {
      return filtered;
    }
    return [effective[0]];
  });

  readonly axisRows = computed(() => {
    const labels = this.axes();
    const list = this.visibleSeries();
    return labels.map((label, idx) => ({
      axis: label,
      entries: list.map((s) => ({
        id: s.id,
        label: s.label,
        color: s.borderColor,
        score: Number((s.values[idx] ?? 0).toFixed(1)),
      })),
    }));
  });

  constructor() {
    effect(() => {
      const canvas = this.canvasRef()?.nativeElement;
      const axisLabels = this.axes();
      const activeSeries = this.visibleSeries();
      const mode = this.viewMode();
      const canRadar = this.hasEnoughAxes();

      if (mode !== 'radar' || !canRadar || !canvas || activeSeries.length === 0) {
        this.destroyChart();
        return;
      }

      this.renderChart(canvas, axisLabels, activeSeries);
    });

    this.destroyRef.onDestroy(() => {
      this.destroyChart();
    });
  }

  toggleSeries(seriesId: string): void {
    const effective = this.effectiveSeries();
    const next = new Set(this.hiddenSeriesIds());
    if (next.has(seriesId)) {
      next.delete(seriesId);
    } else {
      // Keep at least one series visible when toggling
      const visibleCount = effective.filter((item) => !next.has(item.id)).length;
      if (visibleCount > 1) {
        next.add(seriesId);
      }
    }
    this.hiddenSeriesIds.set(next);
  }

  isHidden(seriesId: string): boolean {
    if (!this.hiddenSeriesIds().has(seriesId)) {
      return false;
    }
    return !this.visibleSeries().some((s) => s.id === seriesId);
  }

  toggleBenchmarkOverlay(): void {
    const nextShow = !this.showBenchmark();
    this.showBenchmark.set(nextShow);
    if (!nextShow) {
      // Never leave every remaining series hidden when turning off the benchmark.
      const remaining = this.effectiveSeries();
      const hidden = this.hiddenSeriesIds();
      if (remaining.length > 0 && remaining.every((s) => hidden.has(s.id))) {
        const cleaned = new Set(hidden);
        cleaned.delete(remaining[0].id);
        this.hiddenSeriesIds.set(cleaned);
      }
    }
  }

  setViewMode(mode: 'radar' | 'table'): void {
    this.viewMode.set(mode);
  }

  private renderChart(
    canvas: HTMLCanvasElement,
    axisLabels: string[],
    activeSeries: RadarChartSeries[]
  ): void {
    let ctx: CanvasRenderingContext2D | null = null;
    try {
      ctx = canvas.getContext('2d');
    } catch {
      ctx = null;
    }

    if (!ctx) {
      this.canvasUnavailable.set(true);
      this.destroyChart();
      return;
    }
    this.canvasUnavailable.set(false);
    this.destroyChart();

    const datasets = activeSeries.map((s) => ({
      label: s.label,
      data: axisLabels.map((_, i) => Number((s.values[i] ?? 0).toFixed(1))),
      borderColor: s.borderColor,
      backgroundColor: s.backgroundColor,
      borderWidth: s.dashed ? 1.8 : 2.4,
      borderDash: s.dashed ? [6, 5] : [],
      pointRadius: s.pointRadius ?? (this.compact() ? 2.5 : 3.5),
      pointHoverRadius: 5.5,
      pointBackgroundColor: s.borderColor,
      pointBorderColor: '#ffffff',
      pointBorderWidth: 1.5,
      fill: !s.dashed,
    }));

    const cfg: ChartConfiguration<'radar'> = {
      type: 'radar',
      data: {
        labels: axisLabels,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 280 },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0f172a',
            titleFont: { size: 12, weight: 'bold' },
            bodyFont: { size: 12 },
            padding: 10,
            callbacks: {
              label: (item) => `${item.dataset.label}: ${item.formattedValue}%`,
            },
          },
        },
        scales: {
          r: {
            min: 0,
            max: 100,
            beginAtZero: true,
            ticks: {
              stepSize: 25,
              backdropColor: 'transparent',
              color: '#64748b',
              font: { size: this.compact() ? 9 : 10, weight: 600 },
              callback: (v) => `${v}%`,
            },
            grid: {
              color: '#e2e8f0',
              lineWidth: 1,
            },
            angleLines: {
              color: '#cbd5e1',
              lineWidth: 1,
            },
            pointLabels: {
              color: '#1e293b',
              font: {
                size: this.compact() ? 10.5 : 12,
                weight: 600,
              },
              padding: this.compact() ? 6 : 10,
            },
          },
        },
      },
    };

    this.chartInstance = new Chart(ctx, cfg);
  }

  private destroyChart(): void {
    if (this.chartInstance) {
      this.chartInstance.destroy();
      this.chartInstance = null;
    }
  }
}

