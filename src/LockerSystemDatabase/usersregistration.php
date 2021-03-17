<?php
session_start();
if(isset($_SESSION["loggedin"]) != true) {
    header('Location: login.php');
    exit;
} else {
    $servername = "localhost";
    $username = $_SESSION["username"];
    $password = $_SESSION["password"];
    $dbname = "LOCKER_SYSTEM";
    $conn = mysqli_connect($servername, $username, $password, $dbname);
    $sql = "SELECT * FROM USER_REGISTRATION";
    $result = mysqli_query($conn, $sql);
}
?>
<html>
<header>
    <meta charseet="utf-8">
    <title>Gp3_8 Database</title>
    <link rel="stylesheet" href="bootstrap.min.css">
    <script src="bootstrap.min.js"></script>
</header>
<body>
    <nav class="navbar navbar-default">
        <div class="container-fluid">
            <div class="navbar-header">
                <a class="navbar-brand" href="welcome.php">Gp3_8 Locker System Database</a>
            </div>
            <ul class="nav navbar-nav">
                <li class="nav-item">
                    <a href="usersregistration.php" class="nav-link active">User registration</a>
                </li>
                <li class="nav-item">
                    <a href="historyrecord.php" class="nav-link">History record</a>
                </li>
            </ul>
        </div>
    </nav>
    <head>
        <form method="post" action="usersregistration.php">
            <input type="text" name="search_data" placeholder="Search for ......">
            <select name="search_field">
                <option value="">Select Filter</option>
                <option value="STUDENT_ID">Student ID</option>
                <option value="STUDENT_NAME">Student Name</option>
                <option value="UID">UID</option>
                <option value="REGISTRATION_TIME">Registeration Time</option>
            </select>
            <input type="submit" name="submit" value="Find">
        </form>
    </head>
    <?php
    if (isset($_POST['submit'])) {
        $search_data = $conn -> real_escape_string ($_POST['search_data']);
        $search_field = $conn -> real_escape_string ($_POST['search_field']);
        if ($search_field == "") {
            $search_field = "STUDENT_NAME";
        }
        $search_sql = "SELECT * FROM USER_REGISTRATION WHERE " . $search_field . " LIKE '%" . $search_data . "%'";
        $result = mysqli_query($conn, $search_sql);
    }
    ?>
    <div class="container">
        <h2>Users Registration</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Student ID</th>
                    <th>Student Name</th>
                    <th>UID</th>
                    <th>Registration</th>
                </tr>
            </thead>
            <tbody>
                <?php
                if (mysqli_num_rows($result) > 0) {
                    while($row = mysqli_fetch_assoc($result)) {
                        echo '<tr>';
                        echo '<td>' . $row['ID'] . '</td>';
                        echo '<td>' . $row['STUDENT_ID'] . '</td>';
                        echo '<td>' . $row['STUDENT_NAME'] . '</td>';
                        echo '<td>' . $row['UID'] . '</td>';
                        echo '<td>' . $row['REGISTRATION_TIME'] . '</td>';
                        echo '</tr>';
                    }
                }
                ?>
            </tbody>
        </table>
    </div>
</body>
</html>