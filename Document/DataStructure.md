# Data Structure
|  Sector x |      Block 4x     |         Block 4x+1        |            Block 4x+2            |   Block 4x+3  |      Comment      | Universal Key |
|:---------:|:-----------------:|:-------------------------:|:--------------------------------:|:-------------:|:-----------------:|:-------------:|
|  Sector 0 |     Manufacturer Code     | AuthID w/ StudentID [0:6] |        StudentName [6:31]        |  Sector 0 Key |   Student Info    |      Yes      |
|  Sector 1 | sign [0] + Balance [0:15] |          [0] * 16         |             [0] * 16             |  Sector 1 Key |   Balance Sector  |       No      |
|  Sector 2 |         WriteFlat         |          StartFlat        |             [0] * 16             |  Sector 2 Key |      Indexing     |       No      |
|  Sector 3 |     SystemName [0:30]     |      LockerID [30:31]     | StartTime [0:8] + EndTime [8:15] |  Sector 3 Key |  Use History #1   |       No      |
|    ...    |            ...            |            ...            |                ...               |      ...      |  Use History #2-9 |       No      |
| Sector 12 |     SystemName [0:30]     |      LockerID [30:31]     | StartTime [0:8] + EndTime [8:15] | Sector 12 Key |  Use History #10  |       No      |
| Sector 13 |          [0] * 16         |          [0] * 16         |             [0] * 16             | Sector 13 Key |     Unplanned     |       No      |
| Sector 14 |          [0] * 16         |          [0] * 16         |             [0] * 16             | Sector 14 Key |     Unplanned     |       No      |
| Sector 15 |          [0] * 16         |          [0] * 16         |             [0] * 16             | Sector 15 Key |     Unplanned     |       No      |
