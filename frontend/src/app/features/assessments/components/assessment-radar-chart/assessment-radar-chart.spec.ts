import { describe, expect, it } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import {
  AssessmentRadarChartComponent,
  RadarChartSeries,
} from './assessment-radar-chart';

describe('AssessmentRadarChartComponent', () => {
  async function createFixture(): Promise<{
    fixture: ComponentFixture<AssessmentRadarChartComponent>;
    component: AssessmentRadarChartComponent;
  }> {
    await TestBed.configureTestingModule({
      imports: [AssessmentRadarChartComponent],
      providers: [provideZonelessChangeDetection()],
    }).compileComponents();

    const fixture = TestBed.createComponent(AssessmentRadarChartComponent);
    return { fixture, component: fixture.componentInstance };
  }

  const candidateA: RadarChartSeries = {
    id: 'cand-1',
    label: 'Alice Strong',
    values: [92, 84, 78],
    borderColor: '#4f46e5',
    backgroundColor: 'rgba(79, 70, 229, 0.2)',
    seriesType: 'candidate',
    overallPercentage: 84.7,
  };

  it('renders empty state when axes or series are empty', async () => {
    const { fixture } = await createFixture();
    fixture.componentRef.setInput('emptyMessage', 'No spider data available yet.');
    fixture.detectChanges();
    await fixture.whenStable();

    const emptyEl = fixture.nativeElement.querySelector('.radar-empty');
    expect(emptyEl?.textContent).toContain('No spider data available yet.');
  });

  it('renders 3+ dimensions with benchmark overlay toggle and legend visibility guard', async () => {
    const { fixture, component } = await createFixture();
    fixture.componentRef.setInput('axes', ['Algorithms', 'Data Structures', 'Complexity']);
    fixture.componentRef.setInput('series', [candidateA]);
    fixture.componentRef.setInput('allowBenchmarkToggle', true);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.hasEnoughAxes()).toBe(true);
    expect(component.effectiveSeries().length).toBe(2);

    const pills = fixture.nativeElement.querySelectorAll('.legend-pill') as NodeListOf<HTMLButtonElement>;
    expect(pills.length).toBe(2);
    expect(pills[0].textContent).toContain('Alice Strong');
    expect(pills[1].textContent).toContain('Readiness Target (75%)');

    // Toggle first series off, then verify second (last remaining) cannot be toggled off
    pills[0].click();
    fixture.detectChanges();
    expect(component.isHidden('cand-1')).toBe(true);

    pills[1].click();
    fixture.detectChanges();
    expect(component.isHidden('__benchmark_target__')).toBe(false);

    // Toggle benchmark overlay off via toolbar button
    const benchBtn = fixture.nativeElement.querySelector('.tool-chip') as HTMLButtonElement;
    expect(benchBtn.textContent).toContain('Hide 75% Target');
    benchBtn.click();
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.showBenchmark()).toBe(false);
    expect(component.effectiveSeries().length).toBe(1);
    expect(component.visibleSeries().map((s) => s.id)).toEqual(['cand-1']);
  });

  it('falls back to comparative dimension bars when fewer than 3 axes exist', async () => {
    const { fixture, component } = await createFixture();
    fixture.componentRef.setInput('axes', ['Grammar Mechanics', 'Coherence']);
    fixture.componentRef.setInput('series', [
      {
        ...candidateA,
        values: [88, 72],
      },
    ]);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.hasEnoughAxes()).toBe(false);
    expect(fixture.nativeElement.querySelector('.mode-switch')).toBeNull();
    const axisNote = fixture.nativeElement.querySelector('.axis-note');
    expect(axisNote?.textContent).toContain('at least 3 distinct dimensions');

    const rows = fixture.nativeElement.querySelectorAll('.dim-bar-row');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('Grammar Mechanics');
    expect(rows[0].textContent).toContain('88%');
  });

  it('switches visualization mode between radar and data table', async () => {
    const { fixture, component } = await createFixture();
    fixture.componentRef.setInput('axes', ['Deduction', 'Speed', 'Accuracy']);
    fixture.componentRef.setInput('series', [candidateA]);
    fixture.detectChanges();
    await fixture.whenStable();

    const modeBtns = fixture.nativeElement.querySelectorAll('.mode-btn') as NodeListOf<HTMLButtonElement>;
    expect(modeBtns.length).toBe(2);
    expect(component.viewMode()).toBe('radar');

    modeBtns[1].click();
    fixture.detectChanges();
    expect(component.viewMode()).toBe('table');
    expect(modeBtns[1].classList.contains('active')).toBe(true);
    expect(fixture.nativeElement.querySelector('.fallback-table-wrap')).toBeTruthy();
  });
});

