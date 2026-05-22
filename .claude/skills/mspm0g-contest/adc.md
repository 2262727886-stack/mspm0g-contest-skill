# ADC 采样

## ADC0 单通道

**单通道连续采样：**
```c
volatile uint16_t g_adc_result = 0;

void adc_init(void) {
    // SysConfig: ADC0 → 单通道 → 软件触发 → 12-bit
    DL_ADC12_enableConversions(ADC0);
}

uint16_t adc_read_channel(uint8_t ch) {
    DL_ADC12_setMemAddrMode(ADC0, DL_ADC12_MEM_ADDR_MODE_LARGE_OFFSET,
                             0, DL_ADC12_MEM_ADDR_CTRL_CH(ch), NULL);
    DL_ADC12_startConversion(ADC0);
    while (DL_ADC12_isConversionInProgress(ADC0));
    return DL_ADC12_getMemResult(ADC0, 0);
}
```

**多通道 DMA 采集：**
```c
#define ADC_BUF_SIZE 64
volatile uint16_t adc_buf[ADC_BUF_SIZE];

// SysConfig: ADC0 → Sequence Mode → 触发源=Timer → DMA 自动传输
void adc_dma_init(void) {
    DL_ADC12_enableDMA(ADC0);
    DL_DMA_setSrcAddr(DMA_CH0, (uint32_t)&ADC0->MEMRES[0]);
    DL_DMA_setDstAddr(DMA_CH0, (uint32_t)adc_buf);
    DL_DMA_setTransferSize(DMA_CH0, ADC_BUF_SIZE);
    DL_DMA_enableChannel(DMA_CH0);
    DL_ADC12_startConversion(ADC0);
}
```

