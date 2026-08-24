# Data fences
> Declarative charts, infographics and checksum lists as fenced code blocks.
---
LLMS index: [llms.txt](/llms.txt)
---
## ECharts
```echarts {height="320px"}
xAxis:
type: category
data: [Draft, Review, Published]
yAxis:
type: value
series:
- type: bar
data: [12, 9, 4]
tooltip:
formatter: "$fn:bytesFormatter"
```
## Checksums (Release pack native form)
```checksums {base="https://downloads.example.org/releases/stable" algo="sha256"}
f0b8c9d84dd2b877e0b952130b73e218106fec04c23852271d390213a1ff96f4  pig-1.7.0-1.aarch64.rpm
fbd9b5a696a3cbdcd49ec946664bcdb4a7963919380d3809beb5cefdcfe8bcdf  pig-1.7.0-1.x86_64.rpm
```
## Mermaid
```mermaid
flowchart LR
Fence --> Figure --> Runtime
```
